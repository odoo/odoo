/**
 * @licstart The following is the entire license notice for the
 * JavaScript code in this page
 *
 * Copyright 2024 Mozilla Foundation
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
 * @licend The above is the entire license notice for the
 * JavaScript code in this page
 */

/**
 * pdfjsVersion = 6.5.438
 * pdfjsBuild = 0a4153349
 */

;// ./src/shared/util.js
const isNodeJS = typeof process === "object" && process + "" === "[object process]" && !process.versions.nw && !(process.versions.electron && process.type && process.type !== "browser");
const BBOX_INIT = [Infinity, Infinity, -Infinity, -Infinity];
const F32_BBOX_INIT = new Float32Array(BBOX_INIT);
const FONT_IDENTITY_MATRIX = [0.001, 0, 0, 0.001, 0, 0];
const DEFAULT_VERTICAL_ORIGIN_Y = 880;
const DEFAULT_VERTICAL_ADVANCE = 1000;
const LINE_FACTOR = 1.35;
const LINE_DESCENT_FACTOR = 0.35;
const BASELINE_FACTOR = (/* unused pure expression or super */ null && (LINE_DESCENT_FACTOR / LINE_FACTOR));
const SVG_NS = "http://www.w3.org/2000/svg";
const RenderingIntentFlag = {
  ANY: 0x01,
  DISPLAY: 0x02,
  PRINT: 0x04,
  SAVE: 0x08,
  ANNOTATIONS_FORMS: 0x10,
  ANNOTATIONS_STORAGE: 0x20,
  ANNOTATIONS_DISABLE: 0x40,
  IS_EDITING: 0x80,
  OPLIST: 0x100
};
const AnnotationMode = {
  DISABLE: 0,
  ENABLE: 1,
  ENABLE_FORMS: 2,
  ENABLE_STORAGE: 3
};
const AnnotationPrefix = "pdfjs_internal_id_";
const AnnotationEditorPrefix = "pdfjs_internal_editor_";
const AnnotationEditorType = {
  DISABLE: -1,
  NONE: 0,
  FREETEXT: 3,
  HIGHLIGHT: 9,
  STAMP: 13,
  INK: 15,
  POPUP: 16,
  SIGNATURE: 101,
  COMMENT: 102
};
const AnnotationEditorParamsType = {
  RESIZE: 1,
  CREATE: 2,
  FREETEXT_SIZE: 11,
  FREETEXT_COLOR: 12,
  FREETEXT_OPACITY: 13,
  INK_COLOR: 21,
  INK_THICKNESS: 22,
  INK_OPACITY: 23,
  INK_COLOR_AND_OPACITY: 24,
  HIGHLIGHT_COLOR: 31,
  HIGHLIGHT_THICKNESS: 32,
  HIGHLIGHT_FREE: 33,
  HIGHLIGHT_SHOW_ALL: 34,
  DRAW_STEP: 41
};
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
const MeshFigureType = (/* unused pure expression or super */ null && ({
  TRIANGLES: 1,
  LATTICE: 2,
  PATCH: 3
}));
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
const ImageKind = {
  GRAYSCALE_1BPP: 1,
  RGB_24BPP: 2,
  RGBA_32BPP: 3
};
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
  REDACT: 26,
  RICHMEDIA: 27
};
const AnnotationReplyType = (/* unused pure expression or super */ null && ({
  GROUP: "Group",
  REPLY: "R"
}));
const AnnotationRenditionOperation = (/* unused pure expression or super */ null && ({
  PLAY_OR_RESUME: 0,
  STOP: 1,
  PAUSE: 2,
  RESUME: 3,
  PLAY: 4
}));
const AnnotationFlag = (/* unused pure expression or super */ null && ({
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
}));
const AnnotationFieldFlag = (/* unused pure expression or super */ null && ({
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
}));
const AnnotationBorderStyleType = {
  SOLID: 1,
  DASHED: 2,
  BEVELED: 3,
  INSET: 4,
  UNDERLINE: 5
};
const AnnotationActionEventType = (/* unused pure expression or super */ null && ({
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
}));
const DocumentActionEventType = (/* unused pure expression or super */ null && ({
  WC: "WillClose",
  WS: "WillSave",
  DS: "DidSave",
  WP: "WillPrint",
  DP: "DidPrint"
}));
const PageActionEventType = (/* unused pure expression or super */ null && ({
  O: "PageOpen",
  C: "PageClose"
}));
const VerbosityLevel = {
  ERRORS: 0,
  WARNINGS: 1,
  INFOS: 5
};
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
  beginAnnotation: 80,
  endAnnotation: 81,
  paintImageMaskXObject: 83,
  paintImageMaskXObjectGroup: 84,
  paintImageXObject: 85,
  paintInlineImageXObject: 86,
  paintInlineImageXObjectGroup: 87,
  paintImageXObjectRepeat: 88,
  paintImageMaskXObjectRepeat: 89,
  paintSolidColorImageMask: 90,
  constructPath: 91,
  setStrokeTransparent: 92,
  setFillTransparent: 93,
  rawFillPath: 94
};
const DrawOPS = {
  moveTo: 0,
  lineTo: 1,
  curveTo: 2,
  quadraticCurveTo: 3,
  closePath: 4
};
const PasswordResponses = {
  NEED_PASSWORD: 1,
  INCORRECT_PASSWORD: 2
};
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
    console.info(`Info: ${msg}`);
  }
}
function warn(msg) {
  if (verbosity >= VerbosityLevel.WARNINGS) {
    console.warn(`Warning: ${msg}`);
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
  switch (url?.protocol) {
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
function createValidAbsoluteUrl(url, baseUrl = null, options = null) {
  if (!url) {
    return null;
  }
  if (options && typeof url === "string") {
    if (options.addDefaultProtocol && url.startsWith("www.")) {
      const dots = url.match(/\./g);
      if (dots?.length >= 2) {
        url = `http://${url}`;
      }
    }
    if (options.tryConvertEncoding) {
      try {
        url = stringToUTF8String(url);
      } catch {}
    }
  }
  const absoluteUrl = baseUrl ? URL.parse(url, baseUrl) : URL.parse(url);
  return _isValidProtocol(absoluteUrl) ? absoluteUrl : null;
}
function updateUrlHash(url, hash, allowRel = false) {
  const res = URL.parse(url);
  if (res) {
    res.hash = hash;
    return res.href;
  }
  if (allowRel && createValidAbsoluteUrl(url, "http://example.com")) {
    return url.split("#", 1)[0] + `${hash ? `#${hash}` : ""}`;
  }
  return "";
}
function stripPath(str) {
  return str.substring(str.lastIndexOf("/") + 1);
}
function shadow(obj, prop, value, nonSerializable = false) {
  Object.defineProperty(obj, prop, {
    value,
    enumerable: !nonSerializable,
    configurable: true,
    writable: false
  });
  return value;
}
const BaseException = function BaseExceptionClosure() {
  function BaseException(message, name) {
    this.message = message;
    this.name = name;
  }
  BaseException.prototype = new Error();
  BaseException.constructor = BaseException;
  return BaseException;
}();
class PasswordException extends BaseException {
  constructor(msg, code) {
    super(msg, "PasswordException");
    this.code = code;
  }
}
class UnknownErrorException extends BaseException {
  constructor(msg, details) {
    super(msg, "UnknownErrorException");
    this.details = details;
  }
}
class InvalidPDFException extends BaseException {
  constructor(msg) {
    super(msg, "InvalidPDFException");
  }
}
class ResponseException extends BaseException {
  constructor(msg, status, missing) {
    super(msg, "ResponseException");
    this.status = status;
    this.missing = missing;
  }
}
class FormatError extends BaseException {
  constructor(msg) {
    super(msg, "FormatError");
  }
}
class AbortException extends BaseException {
  constructor(msg) {
    super(msg, "AbortException");
  }
}
function bytesToString(bytes) {
  if (typeof bytes !== "object" || bytes?.length === undefined) {
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
class FeatureTest {
  static get isLittleEndian() {
    const buffer8 = new Uint8Array(4);
    buffer8[0] = 1;
    const view32 = new Uint32Array(buffer8.buffer, 0, 1);
    return shadow(this, "isLittleEndian", view32[0] === 1);
  }
  static get isOffscreenCanvasSupported() {
    return shadow(this, "isOffscreenCanvasSupported", typeof OffscreenCanvas !== "undefined");
  }
  static get isImageDecoderSupported() {
    return shadow(this, "isImageDecoderSupported", typeof ImageDecoder !== "undefined");
  }
  static get isVideoFrameSupported() {
    return shadow(this, "isVideoFrameSupported", typeof VideoFrame !== "undefined");
  }
  static get isFloat16ArraySupported() {
    return shadow(this, "isFloat16ArraySupported", typeof Float16Array !== "undefined");
  }
  static get isSanitizerSupported() {
    return shadow(this, "isSanitizerSupported", typeof Sanitizer !== "undefined");
  }
  static get platform() {
    const {
      platform,
      userAgent
    } = navigator;
    return shadow(this, "platform", {
      isAndroid: userAgent.includes("Android"),
      isLinux: platform.includes("Linux"),
      isMac: platform.includes("Mac"),
      isWindows: platform.includes("Win"),
      isFirefox: userAgent.includes("Firefox")
    });
  }
  static get isCanvasFilterSupported() {
    let ctx;
    if (this.isOffscreenCanvasSupported) {
      ctx = new OffscreenCanvas(1, 1).getContext("2d");
    } else if (typeof document !== "undefined") {
      ctx = document.createElement("canvas").getContext("2d");
    }
    return shadow(this, "isCanvasFilterSupported", ctx?.filter !== undefined);
  }
  static get isAlphaColorInputSupported() {
    if (typeof document === "undefined") {
      return shadow(this, "isAlphaColorInputSupported", false);
    }
    const input = document.createElement("input");
    input.type = "color";
    input.setAttribute("alpha", "");
    input.value = "#ff000080";
    return shadow(this, "isAlphaColorInputSupported", input.value !== "#ff0000");
  }
  static get isBackdropFilterSupported() {
    return shadow(this, "isBackdropFilterSupported", typeof CSS !== "undefined" && CSS.supports("backdrop-filter", "blur(1px)"));
  }
}
class Util {
  static get hexNums() {
    return shadow(this, "hexNums", Array.from({
      length: 256
    }, (_, n) => n.toString(16).padStart(2, "0")));
  }
  static makeHexColor(r, g, b) {
    return `#${this.hexNums[r]}${this.hexNums[g]}${this.hexNums[b]}`;
  }
  static get identity0to256Map() {
    return shadow(this, "identity0to256Map", Uint8Array.from({
      length: 256
    }, (_, i) => i));
  }
  static transform(m1, m2) {
    return [m1[0] * m2[0] + m1[2] * m2[1], m1[1] * m2[0] + m1[3] * m2[1], m1[0] * m2[2] + m1[2] * m2[3], m1[1] * m2[2] + m1[3] * m2[3], m1[0] * m2[4] + m1[2] * m2[5] + m1[4], m1[1] * m2[4] + m1[3] * m2[5] + m1[5]];
  }
  static multiplyByDOMMatrix(m, md) {
    return [m[0] * md.a + m[2] * md.b, m[1] * md.a + m[3] * md.b, m[0] * md.c + m[2] * md.d, m[1] * md.c + m[3] * md.d, m[0] * md.e + m[2] * md.f + m[4], m[1] * md.e + m[3] * md.f + m[5]];
  }
  static applyTransform(p, m, pos = 0) {
    const p0 = p[pos];
    const p1 = p[pos + 1];
    p[pos] = p0 * m[0] + p1 * m[2] + m[4];
    p[pos + 1] = p0 * m[1] + p1 * m[3] + m[5];
  }
  static applyTransformToBezier(p, transform, pos = 0) {
    const m0 = transform[0];
    const m1 = transform[1];
    const m2 = transform[2];
    const m3 = transform[3];
    const m4 = transform[4];
    const m5 = transform[5];
    for (let i = 0; i < 6; i += 2) {
      const pI = p[pos + i];
      const pI1 = p[pos + i + 1];
      p[pos + i] = pI * m0 + pI1 * m2 + m4;
      p[pos + i + 1] = pI * m1 + pI1 * m3 + m5;
    }
  }
  static applyInverseTransform(p, m) {
    const p0 = p[0];
    const p1 = p[1];
    const d = m[0] * m[3] - m[1] * m[2];
    p[0] = (p0 * m[3] - p1 * m[2] + m[2] * m[5] - m[4] * m[3]) / d;
    p[1] = (-p0 * m[1] + p1 * m[0] + m[4] * m[1] - m[5] * m[0]) / d;
  }
  static axialAlignedBoundingBox(rect, transform, output) {
    const m0 = transform[0];
    const m1 = transform[1];
    const m2 = transform[2];
    const m3 = transform[3];
    const m4 = transform[4];
    const m5 = transform[5];
    const r0 = rect[0];
    const r1 = rect[1];
    const r2 = rect[2];
    const r3 = rect[3];
    let a0 = m0 * r0 + m4;
    let a2 = a0;
    let a1 = m0 * r2 + m4;
    let a3 = a1;
    let b0 = m3 * r1 + m5;
    let b2 = b0;
    let b1 = m3 * r3 + m5;
    let b3 = b1;
    if (m1 !== 0 || m2 !== 0) {
      const m1r0 = m1 * r0;
      const m1r2 = m1 * r2;
      const m2r1 = m2 * r1;
      const m2r3 = m2 * r3;
      a0 += m2r1;
      a3 += m2r1;
      a1 += m2r3;
      a2 += m2r3;
      b0 += m1r0;
      b3 += m1r0;
      b1 += m1r2;
      b2 += m1r2;
    }
    output[0] = Math.min(output[0], a0, a1, Math.min(a2, a3));
    output[1] = Math.min(output[1], b0, b1, Math.min(b2, b3));
    output[2] = Math.max(output[2], a0, a1, Math.max(a2, a3));
    output[3] = Math.max(output[3], b0, b1, Math.max(b2, b3));
  }
  static inverseTransform(m) {
    const d = m[0] * m[3] - m[1] * m[2];
    return [m[3] / d, -m[1] / d, -m[2] / d, m[0] / d, (m[2] * m[5] - m[4] * m[3]) / d, (m[4] * m[1] - m[5] * m[0]) / d];
  }
  static singularValueDecompose2dScale(matrix, output) {
    const m0 = matrix[0];
    const m1 = matrix[1];
    const m2 = matrix[2];
    const m3 = matrix[3];
    const a = m0 ** 2 + m1 ** 2;
    const b = m0 * m2 + m1 * m3;
    const c = m2 ** 2 + m3 ** 2;
    const first = (a + c) / 2;
    const second = Math.sqrt(first ** 2 - (a * c - b ** 2));
    output[0] = Math.sqrt(first + second || 1);
    output[1] = Math.sqrt(first - second || 1);
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
    return yLow > yHigh ? null : [xLow, yLow, xHigh, yHigh];
  }
  static pointBoundingBox(x, y, minMax) {
    minMax[0] = Math.min(minMax[0], x);
    minMax[1] = Math.min(minMax[1], y);
    minMax[2] = Math.max(minMax[2], x);
    minMax[3] = Math.max(minMax[3], y);
  }
  static rectBoundingBox(x0, y0, x1, y1, minMax) {
    minMax[0] = Math.min(minMax[0], x0, x1);
    minMax[1] = Math.min(minMax[1], y0, y1);
    minMax[2] = Math.max(minMax[2], x0, x1);
    minMax[3] = Math.max(minMax[3], y0, y1);
  }
  static #getExtremumOnCurve(x0, x1, x2, x3, y0, y1, y2, y3, t, minMax) {
    if (t <= 0 || t >= 1) {
      return;
    }
    const mt = 1 - t;
    const tt = t * t;
    const ttt = tt * t;
    const x = mt * (mt * (mt * x0 + 3 * t * x1) + 3 * tt * x2) + ttt * x3;
    const y = mt * (mt * (mt * y0 + 3 * t * y1) + 3 * tt * y2) + ttt * y3;
    minMax[0] = Math.min(minMax[0], x);
    minMax[1] = Math.min(minMax[1], y);
    minMax[2] = Math.max(minMax[2], x);
    minMax[3] = Math.max(minMax[3], y);
  }
  static #getExtremum(x0, x1, x2, x3, y0, y1, y2, y3, a, b, c, minMax) {
    if (Math.abs(a) < 1e-12) {
      if (Math.abs(b) >= 1e-12) {
        this.#getExtremumOnCurve(x0, x1, x2, x3, y0, y1, y2, y3, -c / b, minMax);
      }
      return;
    }
    const delta = b ** 2 - 4 * c * a;
    if (delta < 0) {
      return;
    }
    const sqrtDelta = Math.sqrt(delta);
    const a2 = 2 * a;
    this.#getExtremumOnCurve(x0, x1, x2, x3, y0, y1, y2, y3, (-b + sqrtDelta) / a2, minMax);
    this.#getExtremumOnCurve(x0, x1, x2, x3, y0, y1, y2, y3, (-b - sqrtDelta) / a2, minMax);
  }
  static bezierBoundingBox(x0, y0, x1, y1, x2, y2, x3, y3, minMax) {
    minMax[0] = Math.min(minMax[0], x0, x3);
    minMax[1] = Math.min(minMax[1], y0, y3);
    minMax[2] = Math.max(minMax[2], x0, x3);
    minMax[3] = Math.max(minMax[3], y0, y3);
    this.#getExtremum(x0, x1, x2, x3, y0, y1, y2, y3, 3 * (-x0 + 3 * (x1 - x2) + x3), 6 * (x0 - 2 * x1 + x2), 3 * (x1 - x0), minMax);
    this.#getExtremum(x0, x1, x2, x3, y0, y1, y2, y3, 3 * (-y0 + 3 * (y1 - y2) + y3), 6 * (y0 - 2 * y1 + y2), 3 * (y1 - y0), minMax);
  }
}
function stringToUTF8String(str) {
  return decodeURIComponent(escape(str));
}
function utf8StringToString(str) {
  return unescape(encodeURIComponent(str));
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
let NormalizeRegex = null;
let NormalizationMap = null;
function normalizeUnicode(str) {
  if (!NormalizeRegex) {
    NormalizeRegex = /([\u00a0\u00b5\u037e\u0eb3\u2000-\u200a\u202f\u2126\ufb00-\ufb04\ufb06\ufb20-\ufb36\ufb38-\ufb3c\ufb3e\ufb40\ufb41\ufb43\ufb44\ufb46-\ufba1\ufba4-\ufba9\ufbae-\ufbb1\ufbd3-\ufbdc\ufbde-\ufbe7\ufbea-\ufbf8\ufbfc\ufbfd\ufc00-\ufc5d\ufc64-\ufcf1\ufcf5-\ufd3d\ufd88\ufdf4\ufdfa\ufdfb\ufe71\ufe77\ufe79\ufe7b\ufe7d]+)|(\ufb05+)/gu;
    NormalizationMap = new Map([["ﬅ", "ſt"]]);
  }
  return str.replaceAll(NormalizeRegex, (_, p1, p2) => p1 ? p1.normalize("NFKC") : NormalizationMap.get(p2));
}
function getUuid() {
  if (typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  const buf = new Uint8Array(32);
  crypto.getRandomValues(buf);
  return bytesToString(buf);
}
function _isValidExplicitDest(validRef, validName, dest) {
  if (!Array.isArray(dest) || dest.length < 2) {
    return false;
  }
  const [page, zoom, ...args] = dest;
  if (!validRef(page) && !Number.isInteger(page)) {
    return false;
  }
  if (!validName(zoom)) {
    return false;
  }
  const argsLen = args.length;
  let allowNull = true;
  switch (zoom.name) {
    case "XYZ":
      if (argsLen < 2 || argsLen > 3) {
        return false;
      }
      break;
    case "Fit":
    case "FitB":
      return argsLen === 0;
    case "FitH":
    case "FitBH":
    case "FitV":
    case "FitBV":
      if (argsLen > 1) {
        return false;
      }
      break;
    case "FitR":
      if (argsLen !== 4) {
        return false;
      }
      allowNull = false;
      break;
    default:
      return false;
  }
  for (const arg of args) {
    if (typeof arg === "number" || allowNull && arg === null) {
      continue;
    }
    return false;
  }
  return true;
}
const makeArr = () => [];
const makeMap = () => new Map();
const makeObj = () => Object.create(null);
const makeSet = () => new Set();
if (typeof Iterator.prototype.join !== "function") {
  Iterator.prototype.join = function (separator) {
    return [...this].join(separator);
  };
}

;// ./src/shared/math_clamp.js
function MathClamp(v, min, max) {
  return Math.min(Math.max(v, min), max);
}

;// ./src/display/display_utils.js


class PixelsPerInch {
  static CSS = 96.0;
  static PDF = 72.0;
  static PDF_TO_CSS_UNITS = this.CSS / this.PDF;
}
class RenderingCancelledException extends BaseException {
  constructor(msg, extraDelay = 0) {
    super(msg, "RenderingCancelledException");
    this.extraDelay = extraDelay;
  }
}
function getRGBA(color) {
  if (color.startsWith("#")) {
    const hex = color.slice(1);
    return [parseInt(hex.slice(0, 2), 16), parseInt(hex.slice(2, 4), 16), parseInt(hex.slice(4, 6), 16), hex.length >= 8 ? parseInt(hex.slice(6, 8), 16) / 255 : 1];
  }
  if (color.startsWith("rgb(")) {
    const [r, g, b] = color.slice(4, -1).split(",").map(x => parseInt(x, 10));
    return [r, g, b, 1];
  }
  if (color.startsWith("rgba(")) {
    const parts = color.slice(5, -1).split(",");
    return [parseInt(parts[0], 10), parseInt(parts[1], 10), parseInt(parts[2], 10), parseFloat(parts[3])];
  }
  const m = color.match(/^color\(srgb\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)(?:\s*\/\s*([\d.]+|none))?\)$/);
  if (m) {
    return [Math.round(parseFloat(m[1]) * 255), Math.round(parseFloat(m[2]) * 255), Math.round(parseFloat(m[3]) * 255), m[4] !== undefined && m[4] !== "none" ? parseFloat(m[4]) : 1];
  }
  return null;
}
function getRGB(color) {
  const rgba = getRGBA(color);
  if (!rgba) {
    warn(`Not a valid color format: "${color}"`);
    return [0, 0, 0];
  }
  return rgba.slice(0, 3);
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
class OutputScale {
  constructor() {
    const {
      pixelRatio
    } = OutputScale;
    this.sx = pixelRatio;
    this.sy = pixelRatio;
  }
  get scaled() {
    return this.sx !== 1 || this.sy !== 1;
  }
  get symmetric() {
    return this.sx === this.sy;
  }
  limitCanvas(width, height, maxPixels, maxDim, capAreaFactor = -1) {
    let maxAreaScale = Infinity,
      maxWidthScale = Infinity,
      maxHeightScale = Infinity;
    maxPixels = OutputScale.capPixels(maxPixels, capAreaFactor);
    if (maxPixels > 0) {
      maxAreaScale = Math.sqrt(maxPixels / (width * height));
    }
    if (maxDim !== -1) {
      maxWidthScale = maxDim / width;
      maxHeightScale = maxDim / height;
    }
    const maxScale = Math.min(maxAreaScale, maxWidthScale, maxHeightScale);
    if (this.sx > maxScale || this.sy > maxScale) {
      this.sx = maxScale;
      this.sy = maxScale;
      return true;
    }
    return false;
  }
  static get pixelRatio() {
    return globalThis.devicePixelRatio || 1;
  }
  static capPixels(maxPixels, capAreaFactor) {
    if (capAreaFactor >= 0) {
      const winPixels = Math.ceil(window.screen.availWidth * window.screen.availHeight * this.pixelRatio ** 2 * (1 + capAreaFactor / 100));
      return maxPixels > 0 ? Math.min(maxPixels, winPixels) : winPixels;
    }
    return maxPixels;
  }
}
function applyOpacity(color, opacity) {
  opacity = MathClamp(opacity ?? 1, 0, 1);
  const white = 255 * (1 - opacity);
  return color.map(c => Math.round(c * opacity + white));
}
function RGBToHSL(rgb, output) {
  const r = rgb[0] / 255;
  const g = rgb[1] / 255;
  const b = rgb[2] / 255;
  const max = Math.max(r, g, b);
  const min = Math.min(r, g, b);
  const l = (max + min) / 2;
  if (max === min) {
    output[0] = output[1] = 0;
  } else {
    const d = max - min;
    output[1] = l < 0.5 ? d / (max + min) : d / (2 - max - min);
    switch (max) {
      case r:
        output[0] = ((g - b) / d + (g < b ? 6 : 0)) * 60;
        break;
      case g:
        output[0] = ((b - r) / d + 2) * 60;
        break;
      case b:
        output[0] = ((r - g) / d + 4) * 60;
        break;
    }
  }
  output[2] = l;
}
function HSLToRGB(hsl, output) {
  const h = hsl[0];
  const s = hsl[1];
  const l = hsl[2];
  const c = (1 - Math.abs(2 * l - 1)) * s;
  const x = c * (1 - Math.abs(h / 60 % 2 - 1));
  const m = l - c / 2;
  switch (Math.floor(h / 60)) {
    case 0:
      output[0] = c + m;
      output[1] = x + m;
      output[2] = m;
      break;
    case 1:
      output[0] = x + m;
      output[1] = c + m;
      output[2] = m;
      break;
    case 2:
      output[0] = m;
      output[1] = c + m;
      output[2] = x + m;
      break;
    case 3:
      output[0] = m;
      output[1] = x + m;
      output[2] = c + m;
      break;
    case 4:
      output[0] = x + m;
      output[1] = m;
      output[2] = c + m;
      break;
    case 5:
    case 6:
      output[0] = c + m;
      output[1] = m;
      output[2] = x + m;
      break;
  }
}
function computeLuminance(x) {
  return x <= 0.03928 ? x / 12.92 : ((x + 0.055) / 1.055) ** 2.4;
}
function contrastRatio(hsl1, hsl2, output) {
  HSLToRGB(hsl1, output);
  output.map(computeLuminance);
  const lum1 = 0.2126 * output[0] + 0.7152 * output[1] + 0.0722 * output[2];
  HSLToRGB(hsl2, output);
  output.map(computeLuminance);
  const lum2 = 0.2126 * output[0] + 0.7152 * output[1] + 0.0722 * output[2];
  return lum1 > lum2 ? (lum1 + 0.05) / (lum2 + 0.05) : (lum2 + 0.05) / (lum1 + 0.05);
}
const contrastCache = new Map();
function findContrastColor(baseColor, fixedColor) {
  const key = baseColor[0] + baseColor[1] * 0x100 + baseColor[2] * 0x10000 + fixedColor[0] * 0x1000000 + fixedColor[1] * 0x100000000 + fixedColor[2] * 0x10000000000;
  let cachedValue = contrastCache.get(key);
  if (cachedValue) {
    return cachedValue;
  }
  const array = new Float32Array(9);
  const output = array.subarray(0, 3);
  const baseHSL = array.subarray(3, 6);
  RGBToHSL(baseColor, baseHSL);
  const fixedHSL = array.subarray(6, 9);
  RGBToHSL(fixedColor, fixedHSL);
  const isFixedColorDark = fixedHSL[2] < 0.5;
  const minContrast = isFixedColorDark ? 12 : 4.5;
  baseHSL[2] = isFixedColorDark ? Math.sqrt(baseHSL[2]) : 1 - Math.sqrt(1 - baseHSL[2]);
  if (contrastRatio(baseHSL, fixedHSL, output) < minContrast) {
    let start, end;
    if (isFixedColorDark) {
      start = baseHSL[2];
      end = 1;
    } else {
      start = 0;
      end = baseHSL[2];
    }
    const PRECISION = 0.005;
    while (end - start > PRECISION) {
      const mid = baseHSL[2] = (start + end) / 2;
      if (isFixedColorDark === contrastRatio(baseHSL, fixedHSL, output) < minContrast) {
        start = mid;
      } else {
        end = mid;
      }
    }
    baseHSL[2] = isFixedColorDark ? end : start;
  }
  HSLToRGB(baseHSL, output);
  cachedValue = Util.makeHexColor(Math.round(output[0] * 255), Math.round(output[1] * 255), Math.round(output[2] * 255));
  contrastCache.set(key, cachedValue);
  return cachedValue;
}
function makePathFromDrawOPS(data) {
  const path = new Path2D();
  if (!data) {
    return path;
  }
  for (let i = 0, ii = data.length; i < ii;) {
    switch (data[i++]) {
      case DrawOPS.moveTo:
        path.moveTo(data[i++], data[i++]);
        break;
      case DrawOPS.lineTo:
        path.lineTo(data[i++], data[i++]);
        break;
      case DrawOPS.curveTo:
        path.bezierCurveTo(data[i++], data[i++], data[i++], data[i++], data[i++], data[i++]);
        break;
      case DrawOPS.quadraticCurveTo:
        path.quadraticCurveTo(data[i++], data[i++], data[i++], data[i++]);
        break;
      case DrawOPS.closePath:
        path.closePath();
        break;
      default:
        warn(`Unrecognized drawing path operator: ${data[i - 1]}`);
        break;
    }
  }
  return path;
}

;// ./src/display/page_viewport.js

class PageViewport {
  constructor({
    viewBox,
    userUnit,
    scale,
    rotation,
    offsetX = 0,
    offsetY = 0,
    dontFlip = false
  }) {
    this.viewBox = viewBox;
    this.userUnit = userUnit;
    this.scale = scale;
    this.rotation = rotation;
    this.offsetX = offsetX;
    this.offsetY = offsetY;
    scale *= userUnit;
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
      width = (viewBox[3] - viewBox[1]) * scale;
      height = (viewBox[2] - viewBox[0]) * scale;
    } else {
      offsetCanvasX = Math.abs(centerX - viewBox[0]) * scale + offsetX;
      offsetCanvasY = Math.abs(centerY - viewBox[1]) * scale + offsetY;
      width = (viewBox[2] - viewBox[0]) * scale;
      height = (viewBox[3] - viewBox[1]) * scale;
    }
    this.transform = [rotateA * scale, rotateB * scale, rotateC * scale, rotateD * scale, offsetCanvasX - rotateA * scale * centerX - rotateC * scale * centerY, offsetCanvasY - rotateB * scale * centerX - rotateD * scale * centerY];
    this.width = width;
    this.height = height;
  }
  get rawDims() {
    const dims = this.viewBox;
    return shadow(this, "rawDims", {
      pageWidth: dims[2] - dims[0],
      pageHeight: dims[3] - dims[1],
      pageX: dims[0],
      pageY: dims[1]
    });
  }
  clone({
    scale = this.scale,
    rotation = this.rotation,
    offsetX = this.offsetX,
    offsetY = this.offsetY,
    dontFlip = false
  } = {}) {
    return new PageViewport({
      viewBox: this.viewBox.slice(),
      userUnit: this.userUnit,
      scale,
      rotation,
      offsetX,
      offsetY,
      dontFlip
    });
  }
  convertToViewportPoint(x, y) {
    const p = [x, y];
    Util.applyTransform(p, this.transform);
    return p;
  }
  convertToPdfPoint(x, y) {
    const p = [x, y];
    Util.applyInverseTransform(p, this.transform);
    return p;
  }
}

;// ./src/display/xfa_text.js
class XfaText {
  static textContent(xfa) {
    const items = [];
    const output = {
      items,
      styles: Object.create(null)
    };
    function walk(node) {
      if (!node) {
        return;
      }
      let str = null;
      const name = node.name;
      if (name === "#text") {
        str = node.value;
      } else if (!XfaText.shouldBuildText(name)) {
        return;
      } else if (node?.attributes?.textContent) {
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

;// ./src/display/xfa_layer.js



const disallowedRichTextStyleRegExp = /url\(|image-set\(/i;
const disallowedEventHandlerAttrRegExp = /^on/i;
class XfaLayer {
  static get _allowedHtmlElements() {
    return shadow(this, "_allowedHtmlElements", new Set(["a", "b", "br", "button", "div", "i", "img", "input", "label", "li", "ol", "option", "p", "select", "span", "sub", "sup", "textarea", "ul"]));
  }
  static get _allowedSvgElements() {
    return shadow(this, "_allowedSvgElements", new Set(["ellipse", "line", "path", "rect", "svg"]));
  }
  static get _allowedRichTextElements() {
    return shadow(this, "_allowedRichTextElements", new Set(["a", "b", "br", "div", "i", "li", "ol", "p", "span", "sub", "sup", "ul"]));
  }
  static get _allowedRichTextAttributes() {
    return shadow(this, "_allowedRichTextAttributes", new Set(["class", "dir", "style"]));
  }
  static get _allowedRichTextStyles() {
    return shadow(this, "_allowedRichTextStyles", new Set(["color", "font", "fontFamily", "fontSize", "fontStretch", "fontStyle", "fontWeight", "kerningMode", "letterSpacing", "lineHeight", "margin", "marginBottom", "marginLeft", "marginRight", "marginTop", "orphans", "paddingLeft", "paddingRight", "breakAfter", "breakBefore", "breakInside", "tabInterval", "tabStop", "textAlign", "textDecoration", "textIndent", "transform", "verticalAlign", "widows"]));
  }
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
          html.setAttribute("value", storedData.value);
          for (const option of element.children) {
            if (option.attributes.value === storedData.value) {
              option.attributes.selected = true;
            } else if (Object.hasOwn(option.attributes, "selected")) {
              delete option.attributes.selected;
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
  static setAttributes({
    html,
    element,
    storage = null,
    intent,
    linkService
  }) {
    const {
      attributes
    } = element;
    const isHTMLAnchorElement = html instanceof HTMLAnchorElement;
    if (attributes.type === "radio") {
      attributes.name = `${attributes.name}-${intent}`;
    }
    for (const [key, value] of Object.entries(attributes)) {
      if (value === null || value === undefined || disallowedEventHandlerAttrRegExp.test(key)) {
        continue;
      }
      if (intent === "richText" && !this._allowedRichTextAttributes.has(key)) {
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
          if (intent === "richText") {
            const allowedStyles = this._allowedRichTextStyles;
            for (const [styleName, styleValue] of Object.entries(value)) {
              if (allowedStyles.has(styleName) && !disallowedRichTextStyleRegExp.test(styleValue)) {
                html.style[styleName] = styleValue;
              }
            }
          } else {
            Object.assign(html.style, value);
          }
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
      linkService?.addLinkAttributes(html, attributes.href, attributes.newWindow);
    }
    if (storage && attributes.dataId) {
      this.setupStorage(html, attributes.dataId, element, storage);
    }
  }
  static #createElement(name, xmlns, intent) {
    if (intent === "richText") {
      return !xmlns && this._allowedRichTextElements.has(name) ? document.createElement(name) : null;
    }
    if (xmlns) {
      return xmlns === SVG_NS && this._allowedSvgElements.has(name) ? document.createElementNS(SVG_NS, name) : null;
    }
    return this._allowedHtmlElements.has(name) ? document.createElement(name) : null;
  }
  static render(parameters) {
    const storage = parameters.annotationStorage;
    const linkService = parameters.linkService;
    const root = parameters.xfaHtml;
    const intent = parameters.intent || "display";
    const rootHtml = this.#createElement(root.name, root.attributes?.xmlns, intent) ?? document.createElement("div");
    if (root.attributes) {
      this.setAttributes({
        html: rootHtml,
        element: root,
        intent,
        linkService
      });
    }
    const isNotForRichText = intent !== "richText";
    const rootDiv = parameters.div;
    rootDiv.append(rootHtml);
    if (parameters.viewport) {
      const transform = `matrix(${parameters.viewport.transform.join(",")})`;
      rootDiv.style.transform = transform;
    }
    if (isNotForRichText) {
      rootDiv.setAttribute("class", "xfaLayer xfaFont");
    }
    const textDivs = [];
    if (root.children.length === 0) {
      if (root.value) {
        const node = document.createTextNode(root.value);
        rootHtml.append(node);
        if (isNotForRichText && XfaText.shouldBuildText(root.name)) {
          textDivs.push(node);
        }
      }
      return {
        textDivs
      };
    }
    const stack = [[root, -1, rootHtml]];
    while (stack.length > 0) {
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
      const childHtml = this.#createElement(name, child.attributes?.xmlns, intent);
      if (!childHtml) {
        continue;
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
      if (child.children?.length > 0) {
        stack.push([child, -1, childHtml]);
      } else if (child.value) {
        const node = document.createTextNode(child.value);
        if (isNotForRichText && XfaText.shouldBuildText(name)) {
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
  static getPageViewport(xfaPage, {
    scale = 1,
    rotation = 0
  }) {
    const {
      width,
      height
    } = xfaPage.attributes.style;
    return new PageViewport({
      viewBox: [0, 0, parseInt(width, 10), parseInt(height, 10)],
      userUnit: 1,
      scale,
      rotation
    });
  }
}

;// ./src/display/dom_utils.js




async function fetchData(url, type = "text") {
  if (isValidFetchUrl(url, document.baseURI)) {
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(response.statusText);
    }
    switch (type) {
      case "blob":
        return response.blob();
      case "bytes":
        return response.bytes();
      case "json":
        return response.json();
    }
    return response.text();
  }
  return new Promise((resolve, reject) => {
    const request = new XMLHttpRequest();
    request.open("GET", url, true);
    request.responseType = type === "bytes" ? "arraybuffer" : type;
    request.onreadystatechange = () => {
      if (request.readyState !== XMLHttpRequest.DONE) {
        return;
      }
      if (request.status === 200 || request.status === 0) {
        switch (type) {
          case "bytes":
            resolve(new Uint8Array(request.response));
            return;
          case "blob":
          case "json":
            resolve(request.response);
            return;
        }
        resolve(request.responseText);
        return;
      }
      reject(new Error(request.statusText));
    };
    request.send(null);
  });
}
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
  [url] = url.split(/[#?]/, 1);
  return stripPath(url);
}
function getPdfFilenameFromUrl(url, defaultFilename = "document.pdf") {
  if (typeof url !== "string") {
    return defaultFilename;
  }
  if (isDataScheme(url)) {
    warn('getPdfFilenameFromUrl: ignore "data:"-URL for performance reasons.');
    return defaultFilename;
  }
  const getURL = urlString => {
    try {
      return new URL(urlString);
    } catch {}
    try {
      return new URL(decodeURIComponent(urlString));
    } catch {}
    try {
      return new URL(urlString, "https://foo.bar");
    } catch {}
    try {
      return new URL(decodeURIComponent(urlString), "https://foo.bar");
    } catch {}
    return null;
  };
  const newURL = getURL(url);
  if (!newURL) {
    return defaultFilename;
  }
  const decode = name => {
    try {
      let decoded = decodeURIComponent(name);
      if (decoded.includes("/")) {
        decoded = stripPath(decoded);
        if (decoded.length === 4 && pdfRegex.test(decoded)) {
          return name;
        }
      }
      return decoded;
    } catch {
      return name;
    }
  };
  const pdfRegex = /\.pdf$/i;
  const filename = stripPath(newURL.pathname);
  if (pdfRegex.test(filename)) {
    return decode(filename);
  }
  if (newURL.searchParams.size > 0) {
    const getLast = iterator => [...iterator].findLast(v => pdfRegex.test(v));
    const name = getLast(newURL.searchParams.values()) ?? getLast(newURL.searchParams.keys());
    if (name) {
      return decode(name);
    }
  }
  if (newURL.hash) {
    const {
      hash
    } = newURL;
    let extensionStart = -1;
    for (const {
      index
    } of hash.matchAll(/\.pdf\b/gi)) {
      extensionStart = index;
    }
    if (extensionStart > 0) {
      let filenameStart = extensionStart;
      while (filenameStart > 0 && !"/?#=".includes(hash[filenameStart - 1])) {
        filenameStart--;
      }
      if (filenameStart < extensionStart) {
        return decode(hash.slice(filenameStart, extensionStart + 4));
      }
    }
  }
  return defaultFilename;
}
function isValidFetchUrl(url, baseUrl) {
  const res = baseUrl ? URL.parse(url, baseUrl) : URL.parse(url);
  return /https?:/.test(res?.protocol ?? "");
}
function noContextMenu(e) {
  e.preventDefault();
}
function stopEvent(e) {
  e.preventDefault();
  e.stopPropagation();
}
class PDFDateString {
  static #regex;
  static toDateObject(input) {
    if (input instanceof Date) {
      return input;
    }
    if (!input || typeof input !== "string") {
      return null;
    }
    this.#regex ||= new RegExp("^D:" + "(\\d{4})" + "(\\d{2})?" + "(\\d{2})?" + "(\\d{2})?" + "(\\d{2})?" + "(\\d{2})?" + "([Z|+\\-])?" + "(\\d{2})?" + "'?" + "(\\d{2})?" + "'?");
    const matches = this.#regex.exec(input);
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
function getColorValues(colors) {
  const span = document.createElement("span");
  span.style.visibility = "hidden";
  span.style.colorScheme = "only light";
  document.body.append(span);
  for (const name of colors.keys()) {
    span.style.color = name;
    const computedColor = window.getComputedStyle(span).color;
    colors.set(name, getRGB(computedColor));
  }
  span.remove();
}
function setLayerDimensions(div, viewport, mustFlip = false, mustRotate = true) {
  if (viewport instanceof PageViewport) {
    const {
      pageWidth,
      pageHeight
    } = viewport.rawDims;
    const {
      style
    } = div;
    const widthStr = `round(down, var(--total-scale-factor) * ${pageWidth}px, var(--scale-round-x))`,
      heightStr = `round(down, var(--total-scale-factor) * ${pageHeight}px, var(--scale-round-y))`;
    if (!mustFlip || viewport.rotation % 180 === 0) {
      style.width = widthStr;
      style.height = heightStr;
    } else {
      style.width = heightStr;
      style.height = widthStr;
    }
  }
  if (mustRotate) {
    div.setAttribute("data-main-rotation", viewport.rotation);
  }
}
const SupportedImageMimeTypes = new Set(["image/apng", "image/avif", "image/bmp", "image/gif", "image/jpeg", "image/png", "image/svg+xml", "image/webp", "image/x-icon"]);
class ColorScheme {
  static get isDarkMode() {
    return shadow(this, "isDarkMode", !!window?.matchMedia?.("(prefers-color-scheme: dark)").matches);
  }
}
class CSSConstants {
  static get commentForegroundColor() {
    const element = document.createElement("span");
    element.classList.add("comment", "sidebar");
    const {
      style
    } = element;
    style.width = style.height = "0";
    style.display = "none";
    style.color = "var(--comment-fg-color)";
    document.body.append(element);
    const {
      color
    } = window.getComputedStyle(element);
    element.remove();
    return shadow(this, "commentForegroundColor", getRGB(color));
  }
}
function renderRichText({
  html,
  dir,
  className
}, container) {
  const fragment = document.createDocumentFragment();
  if (typeof html === "string") {
    const p = document.createElement("p");
    p.dir = dir || "auto";
    const lines = html.split(/\r\n?|\n/);
    for (let i = 0, ii = lines.length; i < ii; ++i) {
      const line = lines[i];
      p.append(document.createTextNode(line));
      if (i < ii - 1) {
        p.append(document.createElement("br"));
      }
    }
    fragment.append(p);
  } else {
    XfaLayer.render({
      xfaHtml: html,
      div: fragment,
      intent: "richText"
    });
  }
  fragment.firstElementChild.classList.add("richText", className);
  container.append(fragment);
}

;// ./src/display/editor/toolbar.js

class EditorToolbar {
  #toolbar = null;
  #colorPicker = null;
  #editor;
  #buttons = null;
  #altText = null;
  #comment = null;
  #commentButtonDivider = null;
  #signatureDescriptionButton = null;
  static #l10nRemove = null;
  constructor(editor) {
    this.#editor = editor;
    EditorToolbar.#l10nRemove ||= Object.freeze({
      freetext: "pdfjs-editor-remove-freetext-button",
      highlight: "pdfjs-editor-remove-highlight-button",
      ink: "pdfjs-editor-remove-ink-button",
      stamp: "pdfjs-editor-remove-stamp-button",
      signature: "pdfjs-editor-remove-signature-button"
    });
  }
  render() {
    const editToolbar = this.#toolbar = document.createElement("div");
    editToolbar.classList.add("editToolbar", "hidden");
    editToolbar.setAttribute("role", "toolbar");
    const signal = this.#editor._uiManager._signal;
    if (signal instanceof AbortSignal && !signal.aborted) {
      editToolbar.addEventListener("contextmenu", noContextMenu, {
        signal
      });
      editToolbar.addEventListener("pointerdown", EditorToolbar.#pointerDown, {
        signal
      });
    }
    const buttons = this.#buttons = document.createElement("div");
    buttons.className = "buttons";
    editToolbar.append(buttons);
    const position = this.#editor.toolbarPosition;
    if (position) {
      const {
        style
      } = editToolbar;
      const x = this.#editor._uiManager.direction === "ltr" ? 1 - position[0] : position[0];
      style.insetInlineEnd = `${100 * x}%`;
      style.top = `calc(${100 * position[1]}% + var(--editor-toolbar-vert-offset))`;
    }
    return editToolbar;
  }
  get div() {
    return this.#toolbar;
  }
  static #pointerDown(e) {
    e.stopPropagation();
  }
  #focusIn(e) {
    this.#editor._focusEventsAllowed = false;
    stopEvent(e);
  }
  #focusOut(e) {
    this.#editor._focusEventsAllowed = true;
    stopEvent(e);
  }
  #addListenersToElement(element) {
    const signal = this.#editor._uiManager._signal;
    if (!(signal instanceof AbortSignal) || signal.aborted) {
      return false;
    }
    element.addEventListener("focusin", this.#focusIn.bind(this), {
      capture: true,
      signal
    });
    element.addEventListener("focusout", this.#focusOut.bind(this), {
      capture: true,
      signal
    });
    element.addEventListener("contextmenu", noContextMenu, {
      signal
    });
    return true;
  }
  hide() {
    this.#toolbar.classList.add("hidden");
    this.#colorPicker?.hideDropdown();
  }
  show() {
    this.#toolbar.classList.remove("hidden");
    this.#altText?.shown();
    this.#comment?.shown();
  }
  addDeleteButton() {
    const {
      editorType,
      _uiManager
    } = this.#editor;
    const button = document.createElement("button");
    button.classList.add("basic", "deleteButton");
    button.tabIndex = 0;
    button.setAttribute("data-l10n-id", EditorToolbar.#l10nRemove[editorType]);
    if (this.#addListenersToElement(button)) {
      button.addEventListener("click", e => {
        _uiManager.delete();
      }, {
        signal: _uiManager._signal
      });
    }
    this.#buttons.append(button);
  }
  get #divider() {
    const divider = document.createElement("div");
    divider.className = "divider";
    return divider;
  }
  async addAltText(altText) {
    const button = await altText.render();
    this.#addListenersToElement(button);
    this.#buttons.append(button, this.#divider);
    this.#altText = altText;
  }
  addComment(comment, beforeElement = null) {
    if (this.#comment) {
      return;
    }
    const button = comment.renderForToolbar();
    if (!button) {
      return;
    }
    this.#addListenersToElement(button);
    const divider = this.#commentButtonDivider = this.#divider;
    if (!beforeElement) {
      this.#buttons.append(button, divider);
    } else {
      this.#buttons.insertBefore(button, beforeElement);
      this.#buttons.insertBefore(divider, beforeElement);
    }
    this.#comment = comment;
    comment.toolbar = this;
  }
  addColorPicker(colorPicker) {
    if (this.#colorPicker) {
      return;
    }
    this.#colorPicker = colorPicker;
    const button = colorPicker.renderButton();
    this.#addListenersToElement(button);
    this.#buttons.append(button, this.#divider);
  }
  async addEditSignatureButton(signatureManager) {
    const button = this.#signatureDescriptionButton = await signatureManager.renderEditButton(this.#editor);
    if (!button) {
      return;
    }
    this.#addListenersToElement(button);
    this.#buttons.append(button, this.#divider);
  }
  removeButton(name) {
    switch (name) {
      case "comment":
        this.#comment?.removeToolbarCommentButton();
        this.#comment = null;
        this.#commentButtonDivider?.remove();
        this.#commentButtonDivider = null;
        break;
    }
  }
  async addButton(name, tool) {
    switch (name) {
      case "colorPicker":
        if (tool) {
          this.addColorPicker(tool);
        }
        break;
      case "altText":
        if (tool) {
          await this.addAltText(tool);
        }
        break;
      case "editSignature":
        if (tool) {
          await this.addEditSignatureButton(tool);
        }
        break;
      case "delete":
        this.addDeleteButton();
        break;
      case "comment":
        if (tool) {
          this.addComment(tool);
        }
        break;
    }
  }
  async addButtonBefore(name, tool, beforeSelector) {
    if (!tool && name === "comment") {
      return;
    }
    const beforeElement = this.#buttons.querySelector(beforeSelector);
    if (!beforeElement) {
      return;
    }
    if (name === "comment") {
      this.addComment(tool, beforeElement);
    }
  }
  updateEditSignatureButton(description) {
    if (this.#signatureDescriptionButton) {
      this.#signatureDescriptionButton.title = description;
    }
  }
  remove() {
    this.#toolbar.remove();
    this.#colorPicker?.destroy();
    this.#colorPicker = null;
  }
}
class FloatingToolbar {
  #buttons = null;
  #toolbar = null;
  #uiManager;
  constructor(uiManager) {
    this.#uiManager = uiManager;
  }
  #render() {
    const editToolbar = this.#toolbar = document.createElement("div");
    editToolbar.className = "editToolbar";
    editToolbar.setAttribute("role", "toolbar");
    editToolbar.dir = this.#uiManager.direction;
    const signal = this.#uiManager._signal;
    if (signal instanceof AbortSignal && !signal.aborted) {
      editToolbar.addEventListener("contextmenu", noContextMenu, {
        signal
      });
    }
    const buttons = this.#buttons = document.createElement("div");
    buttons.className = "buttons";
    editToolbar.append(buttons);
    if (this.#uiManager.hasCommentManager()) {
      this.#makeButton("commentButton", `pdfjs-comment-floating-button`, "pdfjs-comment-floating-button-label", () => {
        this.#uiManager.commentSelection("floating_button");
      });
    }
    this.#makeButton("highlightButton", `pdfjs-highlight-floating-button1`, "pdfjs-highlight-floating-button-label", () => {
      this.#uiManager.highlightSelection("floating_button");
    });
    return editToolbar;
  }
  #getLastPoint(boxes, isLTR) {
    let lastY = 0;
    let lastX = 0;
    for (const box of boxes) {
      const y = box.y + box.height;
      if (y < lastY) {
        continue;
      }
      const x = box.x + (isLTR ? box.width : 0);
      if (y > lastY) {
        lastX = x;
        lastY = y;
        continue;
      }
      if (isLTR) {
        if (x > lastX) {
          lastX = x;
        }
      } else if (x < lastX) {
        lastX = x;
      }
    }
    return [isLTR ? 1 - lastX : lastX, lastY];
  }
  show(parent, boxes, isLTR) {
    const [x, y] = this.#getLastPoint(boxes, isLTR);
    const {
      style
    } = this.#toolbar ||= this.#render();
    parent.append(this.#toolbar);
    style.insetInlineEnd = `${100 * x}%`;
    style.top = `calc(${100 * y}% + var(--editor-toolbar-vert-offset))`;
  }
  hide() {
    this.#toolbar.remove();
  }
  #makeButton(buttonClass, l10nId, labelL10nId, clickHandler) {
    const button = document.createElement("button");
    button.classList.add("basic", buttonClass);
    button.tabIndex = 0;
    button.setAttribute("data-l10n-id", l10nId);
    const span = document.createElement("span");
    button.append(span);
    span.className = "visuallyHidden";
    span.setAttribute("data-l10n-id", labelL10nId);
    const signal = this.#uiManager._signal;
    if (signal instanceof AbortSignal && !signal.aborted) {
      button.addEventListener("contextmenu", noContextMenu, {
        signal
      });
      button.addEventListener("click", clickHandler, {
        signal
      });
    }
    this.#buttons.append(button);
  }
}

;// ./src/shared/internal_evt.js
const INTERNAL_EVT = "da0de832-0602-4da0-9ece-da36fcb1e1e0";
const internalOpt = Object.freeze({
  internal: INTERNAL_EVT
});

;// ./src/display/editor/tools.js





function bindEvents(obj, element, names) {
  for (const name of names) {
    element.addEventListener(name, obj[name].bind(obj));
  }
}
class CurrentPointers {
  static #pointerId = NaN;
  static #pointerIds = null;
  static #moveTimestamp = NaN;
  static #pointerType = null;
  static initializeAndAddPointerId(pointerId) {
    (CurrentPointers.#pointerIds ||= new Set()).add(pointerId);
  }
  static setPointer(pointerType, pointerId) {
    CurrentPointers.#pointerId ||= pointerId;
    CurrentPointers.#pointerType ??= pointerType;
  }
  static setTimeStamp(timeStamp) {
    CurrentPointers.#moveTimestamp = timeStamp;
  }
  static isSamePointerId(pointerId) {
    return CurrentPointers.#pointerId === pointerId;
  }
  static isSamePointerIdOrRemove(pointerId) {
    if (CurrentPointers.#pointerId === pointerId) {
      return true;
    }
    CurrentPointers.#pointerIds?.delete(pointerId);
    return false;
  }
  static isSamePointerType(pointerType) {
    return CurrentPointers.#pointerType === pointerType;
  }
  static isInitializedAndDifferentPointerType(pointerType) {
    return CurrentPointers.#pointerType !== null && !CurrentPointers.isSamePointerType(pointerType);
  }
  static isSameTimeStamp(timeStamp) {
    return CurrentPointers.#moveTimestamp === timeStamp;
  }
  static isUsingMultiplePointers() {
    return CurrentPointers.#pointerIds?.size >= 1;
  }
  static clearPointerType() {
    CurrentPointers.#pointerType = null;
  }
  static clearPointerIds() {
    CurrentPointers.#pointerId = NaN;
    CurrentPointers.#pointerIds = null;
  }
  static clearTimeStamp() {
    CurrentPointers.#moveTimestamp = NaN;
  }
}
class IdManager {
  #id = 0;
  get id() {
    return `${AnnotationEditorPrefix}${this.#id++}`;
  }
}
class ImageManager {
  #baseId = getUuid();
  #id = 0;
  #cache = null;
  static get _isSVGFittingCanvas() {
    const svg = `data:image/svg+xml;charset=UTF-8,<svg viewBox="0 0 1 1" width="1" height="1" xmlns="${SVG_NS}"><rect width="1" height="1" style="fill:red;"/></svg>`;
    const canvas = new OffscreenCanvas(1, 3);
    const ctx = canvas.getContext("2d", {
      willReadFrequently: true
    });
    const image = new Image();
    image.src = svg;
    const promise = image.decode().then(() => {
      ctx.drawImage(image, 0, 0, 1, 1, 0, 0, 1, 3);
      return new Uint32Array(ctx.getImageData(0, 0, 1, 1).data.buffer)[0] === 0;
    });
    return shadow(this, "_isSVGFittingCanvas", promise);
  }
  async #get(key, rawData) {
    this.#cache ||= new Map();
    let data = this.#cache.get(key);
    if (data === null) {
      return null;
    }
    if (data?.bitmap) {
      data.refCounter += 1;
      return data;
    }
    try {
      data ||= {
        bitmap: null,
        id: `image_${this.#baseId}_${this.#id++}`,
        refCounter: 0,
        isSvg: false
      };
      let image;
      if (typeof rawData === "string") {
        data.url = rawData;
        image = await fetchData(rawData, "blob");
      } else if (rawData instanceof File) {
        image = data.file = rawData;
      } else if (rawData instanceof Blob) {
        image = rawData;
      }
      if (image.type === "image/svg+xml") {
        const mustRemoveAspectRatioPromise = ImageManager._isSVGFittingCanvas;
        const fileReader = new FileReader();
        const imageElement = new Image();
        const imagePromise = new Promise((resolve, reject) => {
          imageElement.onload = () => {
            data.bitmap = imageElement;
            data.isSvg = true;
            resolve();
          };
          fileReader.onload = async () => {
            const url = data.svgUrl = fileReader.result;
            imageElement.src = (await mustRemoveAspectRatioPromise) ? `${url}#svgView(preserveAspectRatio(none))` : url;
          };
          imageElement.onerror = fileReader.onerror = reject;
        });
        fileReader.readAsDataURL(image);
        await imagePromise;
      } else {
        data.bitmap = await createImageBitmap(image);
      }
      data.refCounter = 1;
    } catch (e) {
      warn(e);
      data = null;
    }
    this.#cache.set(key, data);
    if (data) {
      this.#cache.set(data.id, data);
    }
    return data;
  }
  async getFromFile(file) {
    const {
      lastModified,
      name,
      size,
      type
    } = file;
    return this.#get(`${lastModified}_${name}_${size}_${type}`, file);
  }
  async getFromUrl(url) {
    return this.#get(url, url);
  }
  async getFromBlob(id, blobPromise) {
    const blob = await blobPromise;
    return this.#get(id, blob);
  }
  async getFromId(id) {
    this.#cache ||= new Map();
    const data = this.#cache.get(id);
    if (!data) {
      return null;
    }
    if (data.bitmap) {
      data.refCounter += 1;
      return data;
    }
    if (data.file) {
      return this.getFromFile(data.file);
    }
    if (data.blobPromise) {
      const {
        blobPromise
      } = data;
      delete data.blobPromise;
      return this.getFromBlob(data.id, blobPromise);
    }
    return this.getFromUrl(data.url);
  }
  getFromCanvas(id, canvas) {
    this.#cache ||= new Map();
    let data = this.#cache.get(id);
    if (data?.bitmap) {
      data.refCounter += 1;
      return data;
    }
    const offscreen = new OffscreenCanvas(canvas.width, canvas.height);
    const ctx = offscreen.getContext("2d");
    ctx.drawImage(canvas, 0, 0);
    data = {
      bitmap: offscreen.transferToImageBitmap(),
      id: `image_${this.#baseId}_${this.#id++}`,
      refCounter: 1,
      isSvg: false
    };
    this.#cache.set(id, data);
    this.#cache.set(data.id, data);
    return data;
  }
  getSvgUrl(id) {
    const data = this.#cache.get(id);
    return !data?.isSvg ? null : data.svgUrl;
  }
  deleteId(id) {
    this.#cache ||= new Map();
    const data = this.#cache.get(id);
    if (!data) {
      return;
    }
    data.refCounter -= 1;
    if (data.refCounter !== 0) {
      return;
    }
    const {
      bitmap
    } = data;
    if (!data.url && !data.file) {
      const canvas = new OffscreenCanvas(bitmap.width, bitmap.height);
      const ctx = canvas.getContext("bitmaprenderer");
      ctx.transferFromImageBitmap(bitmap);
      data.blobPromise = canvas.convertToBlob();
    }
    bitmap.close?.();
    data.bitmap = null;
  }
  isValidId(id) {
    return id.startsWith(`image_${this.#baseId}_`);
  }
}
class CommandManager {
  #commands = [];
  #locked = false;
  #maxSize;
  #position = -1;
  constructor(maxSize = 128) {
    this.#maxSize = maxSize;
  }
  add({
    cmd,
    undo,
    post,
    mustExec,
    type = NaN,
    overwriteIfSameType = false,
    keepUndo = false
  }) {
    if (mustExec) {
      cmd();
    }
    if (this.#locked) {
      return;
    }
    const save = {
      cmd,
      undo,
      post,
      type
    };
    if (this.#position === -1) {
      if (this.#commands.length > 0) {
        this.#commands.length = 0;
      }
      this.#position = 0;
      this.#commands.push(save);
      return;
    }
    if (overwriteIfSameType && this.#commands[this.#position].type === type) {
      if (keepUndo) {
        save.undo = this.#commands[this.#position].undo;
      }
      this.#commands[this.#position] = save;
      return;
    }
    const next = this.#position + 1;
    if (next === this.#maxSize) {
      this.#commands.splice(0, 1);
    } else {
      this.#position = next;
      if (next < this.#commands.length) {
        this.#commands.splice(next);
      }
    }
    this.#commands.push(save);
  }
  undo() {
    if (this.#position === -1) {
      return;
    }
    this.#locked = true;
    const {
      undo,
      post
    } = this.#commands[this.#position];
    undo();
    post?.();
    this.#locked = false;
    this.#position -= 1;
  }
  redo() {
    if (this.#position < this.#commands.length - 1) {
      this.#position += 1;
      this.#locked = true;
      const {
        cmd,
        post
      } = this.#commands[this.#position];
      cmd();
      post?.();
      this.#locked = false;
    }
  }
  hasSomethingToUndo() {
    return this.#position !== -1;
  }
  hasSomethingToRedo() {
    return this.#position < this.#commands.length - 1;
  }
  cleanType(type) {
    if (this.#position === -1) {
      return;
    }
    for (let i = this.#position; i >= 0; i--) {
      if (this.#commands[i].type !== type) {
        this.#commands.splice(i + 1, this.#position - i);
        this.#position = i;
        return;
      }
    }
    this.#commands.length = 0;
    this.#position = -1;
  }
  destroy() {
    this.#commands = null;
  }
}
class KeyboardManager {
  static ALT = 0x1;
  static CTRL = 0x2;
  static META = 0x4;
  static SHIFT = 0x8;
  constructor(callbacks) {
    this.callbacks = new Map();
    const {
      isMac
    } = FeatureTest.platform;
    for (const [keys, callback, options = {}] of callbacks) {
      const hasMacOverride = keys.some(k => k.startsWith("mac+"));
      for (const key of keys) {
        let shortcut = key;
        if (hasMacOverride) {
          const isMacKey = key.startsWith("mac+");
          if (isMac !== isMacKey) {
            continue;
          }
          if (isMacKey) {
            shortcut = key.slice(4);
          }
        }
        const [keyName, modifiers] = KeyboardManager.#parseShortcut(shortcut);
        if (keyName === null) {
          continue;
        }
        this.callbacks.getOrInsertComputed(keyName, makeArr).push({
          callback,
          options,
          modifiers
        });
      }
    }
  }
  static #parseShortcut(value) {
    let keyPart = null;
    let modifiers = 0;
    for (let part of value.split("+")) {
      part = part.trim();
      if (!part) {
        continue;
      }
      const upper = part.toUpperCase();
      const modifier = KeyboardManager[upper];
      if (modifier) {
        modifiers |= modifier;
        continue;
      }
      if (keyPart !== null) {
        warn(`KeyboardManager: multiple keys in shortcut "${value}"`);
        break;
      }
      keyPart = upper === "SPACE" ? " " : part;
    }
    if (keyPart === null) {
      warn(`KeyboardManager: no key found in shortcut "${value}"`);
    }
    return [keyPart, modifiers];
  }
  static #codeToKey(code) {
    const match = /^(?:Key([A-Z])|(?:Digit|Numpad)(\d))$/.exec(code);
    return !match ? null : match[1]?.toLowerCase() ?? match[2];
  }
  exec(self, event) {
    let shortcuts = this.callbacks.get(event.key);
    if (!shortcuts) {
      if (/^[a-z]$/i.test(event.key)) {
        return;
      }
      const fallback = KeyboardManager.#codeToKey(event.code);
      if (fallback === null || fallback === event.key) {
        return;
      }
      shortcuts = this.callbacks.get(fallback);
      if (!shortcuts) {
        return;
      }
    }
    const eventModifiers = (event.altKey ? KeyboardManager.ALT : 0) | (event.ctrlKey ? KeyboardManager.CTRL : 0) | (event.metaKey ? KeyboardManager.META : 0) | (event.shiftKey ? KeyboardManager.SHIFT : 0);
    const info = shortcuts.find(shortcut => shortcut.modifiers === eventModifiers);
    if (!info) {
      return;
    }
    const {
      callback,
      options: {
        bubbles = false,
        args = [],
        checker = null
      }
    } = info;
    if (checker && !checker(self, event)) {
      return;
    }
    callback.bind(self, ...args, event)();
    if (!bubbles) {
      stopEvent(event);
    }
  }
}
class ColorManager {
  static _colorsMapping = new Map([["CanvasText", [0, 0, 0]], ["Canvas", [255, 255, 255]]]);
  get _colors() {
    const colors = new Map([["CanvasText", null], ["Canvas", null]]);
    getColorValues(colors);
    return shadow(this, "_colors", colors);
  }
  convert(color) {
    const rgb = getRGB(color);
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
    return !rgb ? name : Util.makeHexColor(...rgb);
  }
}
class AnnotationEditorUIManager {
  #abortController = new AbortController();
  #activeEditor = null;
  #allEditableAnnotations = null;
  #allEditors = new Map();
  #allLayers = new Map();
  #savedAllLayers = null;
  #savedEditorsByPage = null;
  #altTextManager = null;
  #annotationStorage = null;
  #changedExistingAnnotations = null;
  #commandManager = new CommandManager();
  #commentManager = null;
  #copyPasteAC = null;
  #currentDrawingSession = null;
  #currentPageIndex = 0;
  #deletedAnnotationsElementIds = new Set();
  #draggingEditors = null;
  #editorTypes = null;
  #editorsToRescale = new Set();
  _editorUndoBar = null;
  #enableHighlightFloatingButton = false;
  #enableUpdatedAddImage = false;
  #enableNewAltTextWhenAddingImage = false;
  #filterFactory = null;
  #focusMainContainerTimeoutId = null;
  #focusManagerAC = null;
  #highlightColors = null;
  #highlightWhenShiftUp = false;
  #floatingToolbar = null;
  #idManager = new IdManager();
  #isEnabled = false;
  #isPointerDown = false;
  #isWaiting = false;
  #keyboardManagerAC = null;
  #lastActiveElement = null;
  #mainHighlightColorPicker = null;
  #missingCanvases = null;
  #mlManager = null;
  #mode = AnnotationEditorType.NONE;
  #selectedEditors = new Set();
  #selectedTextNode = null;
  #signatureManager = null;
  #pageColors = null;
  #showAllStates = null;
  #pdfDocument = null;
  #previousStates = {
    isEditing: false,
    isEmpty: true,
    hasSomethingToUndo: false,
    hasSomethingToRedo: false,
    hasSelectedEditor: false,
    hasSelectedText: false
  };
  #translation = [0, 0];
  #translationTimeoutId = null;
  #container = null;
  #viewer = null;
  #viewerAlert = null;
  #updateModeCapability = null;
  static TRANSLATE_SMALL = 1;
  static TRANSLATE_BIG = 10;
  static get _keyboardManager() {
    const proto = AnnotationEditorUIManager.prototype;
    const arrowChecker = self => self.#container.contains(document.activeElement) && document.activeElement.tagName !== "BUTTON" && self.hasSomethingToControl();
    const textInputChecker = (_self, {
      target: el
    }) => {
      if (el instanceof HTMLInputElement) {
        const {
          type
        } = el;
        return type !== "text" && type !== "number";
      }
      return true;
    };
    const small = this.TRANSLATE_SMALL;
    const big = this.TRANSLATE_BIG;
    return shadow(this, "_keyboardManager", new KeyboardManager([[["ctrl+a", "mac+meta+a"], proto.selectAll, {
      checker: textInputChecker
    }], [["ctrl+z", "mac+meta+z"], proto.undo, {
      checker: textInputChecker
    }], [["ctrl+y", "ctrl+shift+z", "mac+meta+shift+z", "ctrl+shift+Z", "mac+meta+shift+Z"], proto.redo, {
      checker: textInputChecker
    }], [["Backspace", "alt+Backspace", "ctrl+Backspace", "shift+Backspace", "mac+Backspace", "mac+alt+Backspace", "mac+ctrl+Backspace", "Delete", "ctrl+Delete", "shift+Delete", "mac+Delete"], proto.delete, {
      checker: textInputChecker
    }], [["Enter"], proto.addNewEditorFromKeyboard, {
      checker: (self, {
        target: el
      }) => !(el instanceof HTMLButtonElement) && self.#container.contains(el) && !self.isEnterHandled
    }], [["Space"], proto.addNewEditorFromKeyboard, {
      checker: (self, {
        target: el
      }) => !(el instanceof HTMLButtonElement) && self.#container.contains(document.activeElement)
    }], [["Escape"], proto.unselectAll], [["ArrowLeft"], proto.translateSelectedEditors, {
      args: [-small, 0],
      checker: arrowChecker
    }], [["ctrl+ArrowLeft", "mac+shift+ArrowLeft"], proto.translateSelectedEditors, {
      args: [-big, 0],
      checker: arrowChecker
    }], [["ArrowRight"], proto.translateSelectedEditors, {
      args: [small, 0],
      checker: arrowChecker
    }], [["ctrl+ArrowRight", "mac+shift+ArrowRight"], proto.translateSelectedEditors, {
      args: [big, 0],
      checker: arrowChecker
    }], [["ArrowUp"], proto.translateSelectedEditors, {
      args: [0, -small],
      checker: arrowChecker
    }], [["ctrl+ArrowUp", "mac+shift+ArrowUp"], proto.translateSelectedEditors, {
      args: [0, -big],
      checker: arrowChecker
    }], [["ArrowDown"], proto.translateSelectedEditors, {
      args: [0, small],
      checker: arrowChecker
    }], [["ctrl+ArrowDown", "mac+shift+ArrowDown"], proto.translateSelectedEditors, {
      args: [0, big],
      checker: arrowChecker
    }]]));
  }
  constructor(container, viewer, viewerAlert, altTextManager, commentManager, signatureManager, eventBus, pdfDocument, pageColors, highlightColors, enableHighlightFloatingButton, enableUpdatedAddImage, enableNewAltTextWhenAddingImage, mlManager, editorUndoBar, supportsPinchToZoom, keepToolbarInPage) {
    const signal = this._signal = this.#abortController.signal;
    this.#container = container;
    this.#viewer = viewer;
    this.#viewerAlert = viewerAlert;
    this.#altTextManager = altTextManager;
    this.#commentManager = commentManager;
    this.#signatureManager = signatureManager;
    this.#pdfDocument = pdfDocument;
    this._eventBus = eventBus;
    const evtOpts = {
      signal,
      ...internalOpt
    };
    eventBus.on("editingaction", this.onEditingAction.bind(this), evtOpts);
    eventBus.on("pagechanging", this.onPageChanging.bind(this), evtOpts);
    eventBus.on("scalechanging", this.onScaleChanging.bind(this), evtOpts);
    eventBus.on("rotationchanging", this.onRotationChanging.bind(this), evtOpts);
    eventBus.on("setpreference", this.onSetPreference.bind(this), evtOpts);
    eventBus.on("switchannotationeditorparams", evt => this.updateParams(evt.type, evt.value), evtOpts);
    window.addEventListener("pointerdown", () => {
      this.#isPointerDown = true;
    }, {
      capture: true,
      signal
    });
    window.addEventListener("pointerup", () => {
      this.#isPointerDown = false;
    }, {
      capture: true,
      signal
    });
    window.addEventListener("beforeunload", this.endCurrentEditing.bind(this), {
      capture: true,
      signal
    });
    this.#addSelectionListener();
    this.#addDragAndDropListeners();
    this.#addKeyboardManager();
    this.#annotationStorage = pdfDocument.annotationStorage;
    this.#filterFactory = pdfDocument.filterFactory;
    this.#pageColors = pageColors;
    this.#highlightColors = highlightColors || null;
    this.#enableHighlightFloatingButton = enableHighlightFloatingButton;
    this.#enableUpdatedAddImage = enableUpdatedAddImage;
    this.#enableNewAltTextWhenAddingImage = enableNewAltTextWhenAddingImage;
    this.#mlManager = mlManager || null;
    this.viewParameters = {
      realScale: PixelsPerInch.PDF_TO_CSS_UNITS,
      rotation: 0
    };
    this.isShiftKeyDown = false;
    this._editorUndoBar = editorUndoBar || null;
    this._supportsPinchToZoom = supportsPinchToZoom !== false;
    this._keepToolbarInPage = keepToolbarInPage === true;
    commentManager?.setSidebarUiManager(this);
  }
  destroy() {
    this.#updateModeCapability?.resolve();
    this.#updateModeCapability = null;
    this.#abortController?.abort();
    this.#abortController = null;
    this._signal = null;
    for (const layer of this.#allLayers.values()) {
      layer.destroy();
    }
    this.#allLayers.clear();
    this.#allEditors.clear();
    this.#editorsToRescale.clear();
    this.#missingCanvases?.clear();
    this.#activeEditor = null;
    this.#selectedEditors.clear();
    this.#commandManager.destroy();
    this.#altTextManager?.destroy();
    this.#commentManager?.destroy();
    this.#signatureManager?.destroy();
    this.#floatingToolbar?.hide();
    this.#floatingToolbar = null;
    this.#mainHighlightColorPicker?.destroy();
    this.#mainHighlightColorPicker = null;
    this.#allEditableAnnotations = null;
    if (this.#focusMainContainerTimeoutId) {
      clearTimeout(this.#focusMainContainerTimeoutId);
      this.#focusMainContainerTimeoutId = null;
    }
    if (this.#translationTimeoutId) {
      clearTimeout(this.#translationTimeoutId);
      this.#translationTimeoutId = null;
    }
    this._editorUndoBar?.destroy();
    this.#pdfDocument = null;
  }
  combinedSignal(ac) {
    return AbortSignal.any([this._signal, ac.signal]);
  }
  get mlManager() {
    return this.#mlManager;
  }
  get useNewAltTextFlow() {
    return this.#enableUpdatedAddImage;
  }
  get useNewAltTextWhenAddingImage() {
    return this.#enableNewAltTextWhenAddingImage;
  }
  get hcmFilter() {
    return shadow(this, "hcmFilter", this.#pageColors ? this.#filterFactory.addHCMFilter(this.#pageColors.foreground, this.#pageColors.background) : "none");
  }
  get direction() {
    return shadow(this, "direction", getComputedStyle(this.#container).direction);
  }
  get _highlightColors() {
    return shadow(this, "_highlightColors", this.#highlightColors ? new Map(this.#highlightColors.split(",").map(pair => {
      pair = pair.split("=").map(x => x.trim());
      pair[1] = pair[1].toUpperCase();
      return pair;
    })) : null);
  }
  get highlightColors() {
    const {
      _highlightColors
    } = this;
    if (!_highlightColors) {
      return shadow(this, "highlightColors", null);
    }
    const map = new Map();
    const hasHCM = !!this.#pageColors;
    for (const [name, color] of _highlightColors) {
      const isNameForHCM = name.endsWith("_HCM");
      if (hasHCM && isNameForHCM) {
        map.set(name.replace("_HCM", ""), color);
        continue;
      }
      if (!hasHCM && !isNameForHCM) {
        map.set(name, color);
      }
    }
    return shadow(this, "highlightColors", map);
  }
  get highlightColorNames() {
    return shadow(this, "highlightColorNames", this.highlightColors ? new Map(Array.from(this.highlightColors, e => e.reverse())) : null);
  }
  getNonHCMColor(color) {
    if (!this._highlightColors) {
      return color;
    }
    const colorName = this.highlightColorNames.get(color);
    return this._highlightColors.get(colorName) || color;
  }
  getNonHCMColorName(color) {
    return this.highlightColorNames.get(color) || color;
  }
  setCurrentDrawingSession(layer) {
    if (layer) {
      this.unselectAll();
      this.disableUserSelect(true);
    } else {
      this.disableUserSelect(false);
    }
    this.#currentDrawingSession = layer;
  }
  setMainHighlightColorPicker(colorPicker) {
    this.#mainHighlightColorPicker = colorPicker;
  }
  editAltText(editor, firstTime = false) {
    this.#altTextManager?.editAltText(this, editor, firstTime);
  }
  hasCommentManager() {
    return !!this.#commentManager;
  }
  editComment(editor, posX, posY, options) {
    this.#commentManager?.showDialog(this, editor, posX, posY, options);
  }
  selectComment(pageIndex, uid) {
    const layer = this.#allLayers.get(pageIndex);
    const editor = layer?.getEditorByUID(uid);
    editor?.toggleComment(true, true);
  }
  updateComment(editor) {
    this.#commentManager?.updateComment(editor.getData());
  }
  updatePopupColor(editor) {
    this.#commentManager?.updatePopupColor(editor);
  }
  removeComment(editor) {
    this.#commentManager?.removeComments([editor.uid]);
  }
  deleteComment(editor, savedData) {
    const undo = () => {
      editor.comment = savedData;
    };
    const cmd = () => {
      this._editorUndoBar?.show(undo, "comment");
      this.toggleComment(null);
      editor.comment = null;
    };
    this.addCommands({
      cmd,
      undo,
      mustExec: true
    });
  }
  toggleComment(editor, isSelected, visibility = undefined) {
    this.#commentManager?.toggleCommentPopup(editor, isSelected, visibility);
  }
  makeCommentColor(color, opacity) {
    return color && this.#commentManager?.makeCommentColor(color, opacity) || null;
  }
  getCommentDialogElement() {
    return this.#commentManager?.dialogElement || null;
  }
  async waitForEditorsRendered(pageNumber) {
    if (this.#allLayers.has(pageNumber - 1)) {
      return;
    }
    const {
      resolve,
      promise
    } = Promise.withResolvers();
    const onEditorsRendered = evt => {
      if (evt.pageNumber === pageNumber) {
        this._eventBus.off("editorsrendered", onEditorsRendered);
        resolve();
      }
    };
    this._eventBus.on("editorsrendered", onEditorsRendered, internalOpt);
    await promise;
  }
  getSignature(editor) {
    this.#signatureManager?.getSignature({
      uiManager: this,
      editor
    });
  }
  get signatureManager() {
    return this.#signatureManager;
  }
  switchToMode(mode, callback) {
    this._eventBus.on("annotationeditormodechanged", callback, {
      once: true,
      signal: this._signal,
      ...internalOpt
    });
    this._eventBus.dispatch("showannotationeditorui", {
      source: this,
      mode
    });
  }
  setPreference(name, value) {
    this._eventBus.dispatch("setpreference", {
      source: this,
      name,
      value
    });
  }
  onSetPreference({
    name,
    value
  }) {
    switch (name) {
      case "enableNewAltTextWhenAddingImage":
        this.#enableNewAltTextWhenAddingImage = value;
        break;
    }
  }
  onPageChanging({
    pageNumber
  }) {
    this.#currentPageIndex = pageNumber - 1;
  }
  deletePage(id) {
    for (const editor of this.getEditors(id)) {
      editor.remove();
    }
    this.#allLayers.delete(id);
    if (this.#currentPageIndex === id) {
      this.#currentPageIndex = 0;
    }
  }
  focusMainContainer() {
    this.#container.focus();
  }
  findParent(x, y) {
    for (const layer of this.#allLayers.values()) {
      const {
        x: layerX,
        y: layerY,
        width,
        height
      } = layer.div.getBoundingClientRect();
      if (x >= layerX && x <= layerX + width && y >= layerY && y <= layerY + height) {
        return layer;
      }
    }
    return null;
  }
  disableUserSelect(value = false) {
    this.#viewer.classList.toggle("noUserSelect", value);
  }
  addShouldRescale(editor) {
    this.#editorsToRescale.add(editor);
  }
  removeShouldRescale(editor) {
    this.#editorsToRescale.delete(editor);
  }
  onScaleChanging({
    scale
  }) {
    this.commitOrRemove();
    this.viewParameters.realScale = scale * PixelsPerInch.PDF_TO_CSS_UNITS;
    for (const editor of this.#editorsToRescale) {
      editor.onScaleChanging();
    }
    this.#currentDrawingSession?.onScaleChanging();
  }
  onRotationChanging({
    pagesRotation
  }) {
    this.commitOrRemove();
    this.viewParameters.rotation = pagesRotation;
  }
  #getAnchorElementForSelection({
    anchorNode
  }) {
    return anchorNode.nodeType === Node.TEXT_NODE ? anchorNode.parentElement : anchorNode;
  }
  #getLayerForTextLayer(textLayer) {
    const {
      currentLayer
    } = this;
    if (currentLayer.hasTextLayer(textLayer)) {
      return currentLayer;
    }
    for (const layer of this.#allLayers.values()) {
      if (layer.hasTextLayer(textLayer)) {
        return layer;
      }
    }
    return null;
  }
  highlightSelection(methodOfCreation = "", comment = false) {
    const selection = document.getSelection();
    if (!selection || selection.isCollapsed) {
      return;
    }
    const {
      anchorNode,
      anchorOffset,
      focusNode,
      focusOffset
    } = selection;
    const text = selection.toString();
    const anchorElement = this.#getAnchorElementForSelection(selection);
    const textLayer = anchorElement.closest(".textLayer");
    const boxes = this.getSelectionBoxes(textLayer);
    if (!boxes) {
      return;
    }
    selection.empty();
    const layer = this.#getLayerForTextLayer(textLayer);
    const isNoneMode = this.#mode === AnnotationEditorType.NONE;
    const callback = () => {
      const editor = layer?.createAndAddNewEditor({
        x: 0,
        y: 0
      }, false, {
        methodOfCreation,
        boxes,
        anchorNode,
        anchorOffset,
        focusNode,
        focusOffset,
        text
      });
      if (isNoneMode) {
        this.showAllEditors("highlight", true, true);
      }
      if (comment) {
        editor?.editComment();
      }
    };
    if (isNoneMode) {
      this.switchToMode(AnnotationEditorType.HIGHLIGHT, callback);
      return;
    }
    callback();
  }
  commentSelection(methodOfCreation = "") {
    this.highlightSelection(methodOfCreation, true);
  }
  endCurrentEditing() {
    this.commitOrRemove();
    this.currentLayer?.endDrawingSession(false);
  }
  #displayFloatingToolbar() {
    const selection = document.getSelection();
    if (!selection || selection.isCollapsed) {
      return;
    }
    const anchorElement = this.#getAnchorElementForSelection(selection);
    const textLayer = anchorElement.closest(".textLayer");
    const boxes = this.getSelectionBoxes(textLayer);
    if (!boxes) {
      return;
    }
    this.#floatingToolbar ||= new FloatingToolbar(this);
    this.#floatingToolbar.show(textLayer, boxes, this.direction === "ltr");
  }
  getAndRemoveDataFromAnnotationStorage(annotationId) {
    if (!this.#annotationStorage) {
      return null;
    }
    const key = `${AnnotationEditorPrefix}${annotationId}`;
    const storedValue = this.#annotationStorage.getRawValue(key);
    if (storedValue) {
      this.#annotationStorage.remove(key);
    }
    return storedValue;
  }
  addToAnnotationStorage(editor) {
    if (!editor.isEmpty() && this.#annotationStorage && !this.#annotationStorage.has(editor.id)) {
      this.#annotationStorage.setValue(editor.id, editor);
    }
  }
  a11yAlert(messageId, args = null) {
    const viewerAlert = this.#viewerAlert;
    if (!viewerAlert) {
      return;
    }
    viewerAlert.setAttribute("data-l10n-id", messageId);
    if (args) {
      viewerAlert.setAttribute("data-l10n-args", JSON.stringify(args));
    } else {
      viewerAlert.removeAttribute("data-l10n-args");
    }
  }
  #selectionChange() {
    const selection = document.getSelection();
    if (!selection || selection.isCollapsed) {
      if (this.#selectedTextNode) {
        this.#floatingToolbar?.hide();
        this.#selectedTextNode = null;
        this.#dispatchUpdateStates({
          hasSelectedText: false
        });
      }
      return;
    }
    const {
      anchorNode
    } = selection;
    if (anchorNode === this.#selectedTextNode) {
      return;
    }
    const anchorElement = this.#getAnchorElementForSelection(selection);
    const textLayer = anchorElement.closest(".textLayer");
    if (!textLayer) {
      if (this.#selectedTextNode) {
        this.#floatingToolbar?.hide();
        this.#selectedTextNode = null;
        this.#dispatchUpdateStates({
          hasSelectedText: false
        });
      }
      return;
    }
    this.#floatingToolbar?.hide();
    this.#selectedTextNode = anchorNode;
    this.#dispatchUpdateStates({
      hasSelectedText: true
    });
    if (this.#mode !== AnnotationEditorType.HIGHLIGHT && this.#mode !== AnnotationEditorType.NONE) {
      return;
    }
    if (this.#mode === AnnotationEditorType.HIGHLIGHT) {
      this.showAllEditors("highlight", true, true);
    }
    this.#highlightWhenShiftUp = this.isShiftKeyDown;
    if (!this.isShiftKeyDown) {
      const activeLayer = this.#mode === AnnotationEditorType.HIGHLIGHT ? this.#getLayerForTextLayer(textLayer) : null;
      activeLayer?.toggleDrawing();
      if (this.#isPointerDown) {
        const ac = new AbortController();
        const signal = this.combinedSignal(ac);
        const pointerup = e => {
          if (e.type === "pointerup" && e.button !== 0) {
            return;
          }
          ac.abort();
          activeLayer?.toggleDrawing(true);
          if (e.type === "pointerup") {
            this.#onSelectEnd("main_toolbar");
          }
        };
        window.addEventListener("pointerup", pointerup, {
          signal
        });
        window.addEventListener("blur", pointerup, {
          signal
        });
      } else {
        activeLayer?.toggleDrawing(true);
        this.#onSelectEnd("main_toolbar");
      }
    }
  }
  #onSelectEnd(methodOfCreation = "") {
    if (this.#mode === AnnotationEditorType.HIGHLIGHT) {
      this.highlightSelection(methodOfCreation);
    } else if (this.#enableHighlightFloatingButton) {
      this.#displayFloatingToolbar();
    }
  }
  #addSelectionListener() {
    document.addEventListener("selectionchange", this.#selectionChange.bind(this), {
      signal: this._signal
    });
  }
  #addFocusManager() {
    if (this.#focusManagerAC) {
      return;
    }
    this.#focusManagerAC = new AbortController();
    const signal = this.combinedSignal(this.#focusManagerAC);
    window.addEventListener("focus", this.focus.bind(this), {
      signal
    });
    window.addEventListener("blur", this.blur.bind(this), {
      signal
    });
  }
  #removeFocusManager() {
    this.#focusManagerAC?.abort();
    this.#focusManagerAC = null;
  }
  blur() {
    this.isShiftKeyDown = false;
    if (this.#highlightWhenShiftUp) {
      this.#highlightWhenShiftUp = false;
      this.#onSelectEnd("main_toolbar");
    }
    if (!this.hasSelection) {
      return;
    }
    const {
      activeElement
    } = document;
    for (const editor of this.#selectedEditors) {
      if (editor.div.contains(activeElement)) {
        this.#lastActiveElement = [editor, activeElement];
        editor._focusEventsAllowed = false;
        break;
      }
    }
  }
  focus() {
    if (!this.#lastActiveElement) {
      return;
    }
    const [lastEditor, lastActiveElement] = this.#lastActiveElement;
    this.#lastActiveElement = null;
    lastActiveElement.addEventListener("focusin", () => {
      lastEditor._focusEventsAllowed = true;
    }, {
      once: true,
      signal: this._signal
    });
    lastActiveElement.focus();
  }
  #addKeyboardManager() {
    if (this.#keyboardManagerAC) {
      return;
    }
    this.#keyboardManagerAC = new AbortController();
    const signal = this.combinedSignal(this.#keyboardManagerAC);
    window.addEventListener("keydown", this.keydown.bind(this), {
      signal
    });
    window.addEventListener("keyup", this.keyup.bind(this), {
      signal
    });
  }
  #removeKeyboardManager() {
    this.#keyboardManagerAC?.abort();
    this.#keyboardManagerAC = null;
  }
  #addCopyPasteListeners() {
    if (this.#copyPasteAC) {
      return;
    }
    this.#copyPasteAC = new AbortController();
    const signal = this.combinedSignal(this.#copyPasteAC);
    document.addEventListener("copy", this.copy.bind(this), {
      signal
    });
    document.addEventListener("cut", this.cut.bind(this), {
      signal
    });
    document.addEventListener("paste", this.paste.bind(this), {
      signal
    });
  }
  #removeCopyPasteListeners() {
    this.#copyPasteAC?.abort();
    this.#copyPasteAC = null;
  }
  #addDragAndDropListeners() {
    const signal = this._signal;
    document.addEventListener("dragover", this.dragOver.bind(this), {
      signal
    });
    document.addEventListener("drop", this.drop.bind(this), {
      signal
    });
  }
  addEditListeners() {
    this.#addKeyboardManager();
    this.setEditingState(true);
  }
  removeEditListeners() {
    this.#removeKeyboardManager();
    this.setEditingState(false);
  }
  dragOver(event) {
    for (const {
      type
    } of event.dataTransfer.items) {
      for (const editorType of this.#editorTypes) {
        if (editorType.isHandlingMimeForPasting(type)) {
          event.dataTransfer.dropEffect = "copy";
          event.preventDefault();
          return;
        }
      }
    }
  }
  drop(event) {
    for (const item of event.dataTransfer.items) {
      for (const editorType of this.#editorTypes) {
        if (editorType.isHandlingMimeForPasting(item.type)) {
          editorType.paste(item, this.currentLayer);
          event.preventDefault();
          return;
        }
      }
    }
  }
  copy(event) {
    event.preventDefault();
    this.#activeEditor?.commitOrRemove();
    if (!this.hasSelection) {
      return;
    }
    const editors = [];
    for (const editor of this.#selectedEditors) {
      const serialized = editor.serialize(true);
      if (serialized) {
        editors.push(serialized);
      }
    }
    if (editors.length === 0) {
      return;
    }
    event.clipboardData.setData("application/pdfjs", JSON.stringify(editors));
  }
  cut(event) {
    this.copy(event);
    this.delete();
  }
  async paste(event) {
    event.preventDefault();
    const {
      clipboardData
    } = event;
    for (const item of clipboardData.items) {
      for (const editorType of this.#editorTypes) {
        if (editorType.isHandlingMimeForPasting(item.type)) {
          editorType.paste(item, this.currentLayer);
          return;
        }
      }
    }
    let data = clipboardData.getData("application/pdfjs");
    if (!data) {
      return;
    }
    try {
      data = JSON.parse(data);
    } catch (ex) {
      warn(`paste: "${ex.message}".`);
      return;
    }
    if (!Array.isArray(data)) {
      return;
    }
    this.unselectAll();
    const layer = this.currentLayer;
    try {
      const newEditors = [];
      for (const editor of data) {
        const deserializedEditor = await layer.deserialize(editor);
        if (!deserializedEditor) {
          return;
        }
        newEditors.push(deserializedEditor);
      }
      const cmd = () => {
        for (const editor of newEditors) {
          this.#addEditorToLayer(editor);
        }
        this.#selectEditors(newEditors);
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
    } catch (ex) {
      warn(`paste: "${ex.message}".`);
    }
  }
  keydown(event) {
    if (!this.isShiftKeyDown && event.key === "Shift") {
      this.isShiftKeyDown = true;
    }
    if (this.#mode !== AnnotationEditorType.NONE && !this.isEditorHandlingKeyboard) {
      AnnotationEditorUIManager._keyboardManager.exec(this, event);
    }
  }
  keyup(event) {
    if (this.isShiftKeyDown && event.key === "Shift") {
      this.isShiftKeyDown = false;
      if (this.#highlightWhenShiftUp) {
        this.#highlightWhenShiftUp = false;
        this.#onSelectEnd("main_toolbar");
      }
    }
  }
  onEditingAction({
    name
  }) {
    switch (name) {
      case "undo":
      case "redo":
      case "delete":
      case "selectAll":
        this[name]();
        break;
      case "highlightSelection":
        this.highlightSelection("context_menu");
        break;
      case "commentSelection":
        this.commentSelection("context_menu");
        break;
    }
  }
  updatePageIndex(oldPageIndex, newPageIndex) {
    for (const editor of this.#savedEditorsByPage.get(oldPageIndex) || []) {
      editor.pageIndex = newPageIndex;
    }
    const layer = this.#savedAllLayers.get(oldPageIndex);
    if (layer) {
      layer.pageIndex = newPageIndex;
      this.#allLayers.set(newPageIndex, layer);
      if (this.#isEnabled) {
        layer.enable();
      } else {
        layer.disable();
      }
    }
  }
  startUpdatePages() {
    this.#savedAllLayers = new Map(this.#allLayers);
    this.#allLayers.clear();
    const savedEditorsByPage = this.#savedEditorsByPage = new Map();
    const saveEditor = editor => {
      savedEditorsByPage.getOrInsertComputed(editor.pageIndex, makeArr).push(editor);
    };
    for (const editor of this.#allEditors.values()) {
      saveEditor(editor);
    }
    for (const [id, editor] of this.#annotationStorage) {
      if (id.startsWith(AnnotationEditorPrefix) && !this.#allEditors.has(id) && Number.isInteger(editor?.pageIndex)) {
        saveEditor(editor);
      }
    }
  }
  endUpdatePages() {
    this.#savedAllLayers = null;
    this.#savedEditorsByPage = null;
  }
  clonePage(pageIndex, newPageIndex) {
    for (const editor of this.getEditors(pageIndex)) {
      const serialized = editor.serialize(editor.mode !== AnnotationEditorType.HIGHLIGHT);
      if (!serialized) {
        continue;
      }
      serialized.pageIndex = newPageIndex;
      serialized.id = this.getId();
      serialized.isClone = true;
      delete serialized.popupRef;
      this.#annotationStorage.setValue(serialized.id, serialized);
    }
  }
  findClonesForPage(layer) {
    const promises = [];
    const {
      pageIndex
    } = layer;
    for (const [id, editor] of this.#annotationStorage) {
      if (editor.pageIndex === pageIndex && editor.isClone) {
        this.#annotationStorage.remove(id);
        promises.push(layer.deserialize(editor).then(deserializedEditor => {
          if (deserializedEditor) {
            deserializedEditor.isClone = true;
            layer.addOrRebuild(deserializedEditor);
          }
        }));
      }
    }
    return Promise.all(promises);
  }
  #dispatchUpdateStates(details) {
    const hasChanged = Object.entries(details).some(([key, value]) => this.#previousStates[key] !== value);
    if (hasChanged) {
      this._eventBus.dispatch("editingstateschanged", {
        source: this,
        details: Object.assign(this.#previousStates, details)
      });
      if (this.#mode === AnnotationEditorType.HIGHLIGHT && details.hasSelectedEditor === false) {
        this.#dispatchUpdateUI([[AnnotationEditorParamsType.HIGHLIGHT_FREE, true]]);
      }
    }
  }
  #dispatchUpdateUI(details) {
    this._eventBus.dispatch("annotationeditorparamschanged", {
      source: this,
      details
    });
  }
  setEditingState(isEditing) {
    if (isEditing) {
      this.#addFocusManager();
      this.#addCopyPasteListeners();
      this.#dispatchUpdateStates({
        isEditing: this.#mode !== AnnotationEditorType.NONE,
        isEmpty: this.#isEmpty(),
        hasSomethingToUndo: this.#commandManager.hasSomethingToUndo(),
        hasSomethingToRedo: this.#commandManager.hasSomethingToRedo(),
        hasSelectedEditor: false
      });
    } else {
      this.#removeFocusManager();
      this.#removeCopyPasteListeners();
      this.#dispatchUpdateStates({
        isEditing: false
      });
      this.disableUserSelect(false);
    }
  }
  registerEditorTypes(types) {
    if (this.#editorTypes) {
      return;
    }
    this.#editorTypes = types;
    for (const editorType of this.#editorTypes) {
      this.#dispatchUpdateUI(editorType.defaultPropertiesToUpdate);
    }
  }
  getId() {
    return this.#idManager.id;
  }
  get currentLayer() {
    return this.#allLayers.get(this.#currentPageIndex);
  }
  getLayer(pageIndex) {
    return this.#allLayers.get(pageIndex);
  }
  get currentPageIndex() {
    return this.#currentPageIndex;
  }
  addLayer(layer) {
    this.#allLayers.set(layer.pageIndex, layer);
    if (this.#isEnabled) {
      layer.enable();
    } else {
      layer.disable();
    }
  }
  removeLayer(layer) {
    this.#allLayers.delete(layer.pageIndex);
  }
  async updateMode(mode, editId = null, isFromUser = false, isFromKeyboard = false, mustEnterInEditMode = false, editComment = false) {
    if (this.#mode === mode) {
      return;
    }
    if (this.#updateModeCapability) {
      await this.#updateModeCapability.promise;
      if (!this.#updateModeCapability) {
        return;
      }
    }
    this.#updateModeCapability = Promise.withResolvers();
    this.#currentDrawingSession?.commitOrRemove();
    if (this.#mode === AnnotationEditorType.POPUP) {
      this.#commentManager?.hideSidebar();
    }
    this.#commentManager?.destroyPopup();
    this.#mode = mode;
    if (mode === AnnotationEditorType.NONE) {
      this.setEditingState(false);
      this.#disableAll();
      for (const editor of this.#allEditors.values()) {
        editor.hideStandaloneCommentButton();
      }
      this._editorUndoBar?.hide();
      this.toggleComment(null);
      this.#updateModeCapability.resolve();
      return;
    }
    for (const editor of this.#allEditors.values()) {
      editor.addStandaloneCommentButton();
    }
    if (mode === AnnotationEditorType.SIGNATURE) {
      await this.#signatureManager?.loadSignatures();
    }
    if (isFromUser) {
      CurrentPointers.clearPointerType();
    }
    this.setEditingState(true);
    await this.#enableAll();
    this.unselectAll();
    for (const layer of this.#allLayers.values()) {
      layer.updateMode(mode);
    }
    if (mode === AnnotationEditorType.POPUP) {
      this.#allEditableAnnotations ||= await this.#pdfDocument.getAnnotationsByType(new Set(this.#editorTypes.map(editorClass => editorClass._editorType)));
      const elementIds = new Set();
      const allComments = [];
      for (const editor of this.#allEditors.values()) {
        const {
          annotationElementId,
          hasComment,
          deleted
        } = editor;
        if (annotationElementId) {
          elementIds.add(annotationElementId);
        }
        if (hasComment && !deleted) {
          allComments.push(editor.getData());
        }
      }
      for (const annotation of this.#allEditableAnnotations) {
        const {
          id,
          popupRef,
          contentsObj
        } = annotation;
        if (popupRef && contentsObj?.str && !elementIds.has(id) && !this.#deletedAnnotationsElementIds.has(id)) {
          allComments.push(annotation);
        }
      }
      this.#commentManager?.showSidebar(allComments);
    }
    if (!editId) {
      if (isFromKeyboard) {
        this.addNewEditorFromKeyboard();
      }
      this.#updateModeCapability.resolve();
      return;
    }
    for (const editor of this.#allEditors.values()) {
      if (editor.uid === editId) {
        this.setSelected(editor);
        if (editComment) {
          editor.editComment();
        } else if (mustEnterInEditMode) {
          editor.enterInEditMode();
        } else {
          editor.focus();
        }
      } else {
        editor.unselect();
      }
    }
    this.#updateModeCapability.resolve();
  }
  addNewEditorFromKeyboard() {
    if (this.currentLayer.canCreateNewEmptyEditor()) {
      this.currentLayer.addNewEditor();
    }
  }
  updateToolbar(options) {
    if (options.mode === this.#mode) {
      return;
    }
    this._eventBus.dispatch("switchannotationeditormode", {
      source: this,
      ...options
    });
  }
  updateParams(type, value) {
    if (!this.#editorTypes) {
      return;
    }
    switch (type) {
      case AnnotationEditorParamsType.CREATE:
        this.currentLayer.addNewEditor(value);
        return;
      case AnnotationEditorParamsType.HIGHLIGHT_SHOW_ALL:
        this._eventBus.dispatch("reporttelemetry", {
          source: this,
          details: {
            type: "editing",
            data: {
              type: "highlight",
              action: "toggle_visibility"
            }
          }
        });
        (this.#showAllStates ||= new Map()).set(type, value);
        this.showAllEditors("highlight", value);
        break;
    }
    if (this.hasSelection) {
      for (const editor of this.#selectedEditors) {
        editor.updateParams(type, value);
      }
    } else {
      for (const editorType of this.#editorTypes) {
        editorType.updateDefaultParams(type, value);
      }
    }
  }
  showAllEditors(type, visible, updateButton = false) {
    for (const editor of this.#allEditors.values()) {
      if (editor.editorType === type) {
        editor.show(visible);
      }
    }
    const state = this.#showAllStates?.get(AnnotationEditorParamsType.HIGHLIGHT_SHOW_ALL) ?? true;
    if (state !== visible) {
      this.#dispatchUpdateUI([[AnnotationEditorParamsType.HIGHLIGHT_SHOW_ALL, visible]]);
    }
  }
  enableWaiting(mustWait = false) {
    if (this.#isWaiting === mustWait) {
      return;
    }
    this.#isWaiting = mustWait;
    for (const layer of this.#allLayers.values()) {
      if (mustWait) {
        layer.disableClick();
      } else {
        layer.enableClick();
      }
      layer.div.classList.toggle("waiting", mustWait);
    }
  }
  async #enableAll() {
    if (!this.#isEnabled) {
      this.#isEnabled = true;
      const promises = [];
      for (const layer of this.#allLayers.values()) {
        promises.push(layer.enable());
      }
      await Promise.all(promises);
      for (const editor of this.#allEditors.values()) {
        editor.enable();
      }
    }
  }
  #disableAll() {
    this.unselectAll();
    if (this.#isEnabled) {
      this.#isEnabled = false;
      for (const layer of this.#allLayers.values()) {
        layer.disable();
      }
      for (const editor of this.#allEditors.values()) {
        editor.disable();
      }
    }
  }
  *getEditors(pageIndex) {
    for (const editor of this.#allEditors.values()) {
      if (editor.pageIndex === pageIndex) {
        yield editor;
      }
    }
  }
  getEditor(id) {
    return this.#allEditors.get(id);
  }
  addEditor(editor) {
    this.#allEditors.set(editor.id, editor);
  }
  removeEditor(editor) {
    if (editor.div.contains(document.activeElement)) {
      if (this.#focusMainContainerTimeoutId) {
        clearTimeout(this.#focusMainContainerTimeoutId);
      }
      this.#focusMainContainerTimeoutId = setTimeout(() => {
        this.focusMainContainer();
        this.#focusMainContainerTimeoutId = null;
      }, 0);
    }
    this.#allEditors.delete(editor.id);
    if (editor.annotationElementId) {
      this.#missingCanvases?.delete(editor.annotationElementId);
    }
    this.unselect(editor);
    if (!editor.annotationElementId || !this.#deletedAnnotationsElementIds.has(editor.annotationElementId)) {
      this.#annotationStorage?.remove(editor.id);
    }
  }
  addDeletedAnnotationElement(editor) {
    this.#deletedAnnotationsElementIds.add(editor.annotationElementId);
    this.addChangedExistingAnnotation(editor);
    editor.deleted = true;
  }
  isDeletedAnnotationElement(annotationElementId) {
    return this.#deletedAnnotationsElementIds.has(annotationElementId);
  }
  removeDeletedAnnotationElement(editor) {
    this.#deletedAnnotationsElementIds.delete(editor.annotationElementId);
    this.removeChangedExistingAnnotation(editor);
    editor.deleted = false;
  }
  #addEditorToLayer(editor) {
    const layer = this.#allLayers.get(editor.pageIndex);
    if (layer) {
      layer.addOrRebuild(editor);
    } else {
      this.addEditor(editor);
      this.addToAnnotationStorage(editor);
    }
  }
  setActiveEditor(editor) {
    if (this.#activeEditor === editor) {
      return;
    }
    this.#activeEditor = editor;
    if (editor) {
      this.#dispatchUpdateUI(editor.propertiesToUpdate);
    }
  }
  get #lastSelectedEditor() {
    let ed = null;
    for (ed of this.#selectedEditors) {}
    return ed;
  }
  updateUI(editor) {
    if (this.#lastSelectedEditor === editor) {
      this.#dispatchUpdateUI(editor.propertiesToUpdate);
    }
  }
  updateUIForDefaultProperties(editorType) {
    this.#dispatchUpdateUI(editorType.defaultPropertiesToUpdate);
  }
  toggleSelected(editor) {
    if (this.#selectedEditors.has(editor)) {
      this.#selectedEditors.delete(editor);
      editor.unselect();
      this.#dispatchUpdateStates({
        hasSelectedEditor: this.hasSelection
      });
      return;
    }
    this.#selectedEditors.add(editor);
    editor.select();
    this.#dispatchUpdateUI(editor.propertiesToUpdate);
    this.#dispatchUpdateStates({
      hasSelectedEditor: true
    });
  }
  setSelected(editor) {
    this.updateToolbar({
      mode: editor.mode,
      editId: editor.uid
    });
    this.#currentDrawingSession?.commitOrRemove();
    for (const ed of this.#selectedEditors) {
      if (ed !== editor) {
        ed.unselect();
      }
    }
    this.#commentManager?.destroyPopup();
    this.#selectedEditors.clear();
    this.#selectedEditors.add(editor);
    editor.select();
    this.#dispatchUpdateUI(editor.propertiesToUpdate);
    this.#dispatchUpdateStates({
      hasSelectedEditor: true
    });
  }
  get firstSelectedEditor() {
    return this.#selectedEditors.values().next().value;
  }
  unselect(editor) {
    editor.unselect();
    this.#selectedEditors.delete(editor);
    this.#dispatchUpdateStates({
      hasSelectedEditor: this.hasSelection
    });
  }
  get hasSelection() {
    return this.#selectedEditors.size !== 0;
  }
  get isEnterHandled() {
    return this.#selectedEditors.size === 1 && this.firstSelectedEditor.isEnterHandled;
  }
  undo() {
    this.#commandManager.undo();
    this.#dispatchUpdateStates({
      hasSomethingToUndo: this.#commandManager.hasSomethingToUndo(),
      hasSomethingToRedo: this.#commandManager.hasSomethingToRedo(),
      isEmpty: this.#isEmpty()
    });
    this._editorUndoBar?.hide();
  }
  redo() {
    this.#commandManager.redo();
    this.#dispatchUpdateStates({
      hasSomethingToUndo: this.#commandManager.hasSomethingToUndo(),
      hasSomethingToRedo: this.#commandManager.hasSomethingToRedo(),
      isEmpty: this.#isEmpty()
    });
  }
  addCommands(params) {
    this.#commandManager.add(params);
    this.#dispatchUpdateStates({
      hasSomethingToUndo: true,
      hasSomethingToRedo: false,
      isEmpty: this.#isEmpty()
    });
  }
  cleanUndoStack(type) {
    this.#commandManager.cleanType(type);
  }
  #isEmpty() {
    if (this.#allEditors.size === 0) {
      return true;
    }
    if (this.#allEditors.size === 1) {
      for (const editor of this.#allEditors.values()) {
        return editor.isEmpty();
      }
    }
    return false;
  }
  delete() {
    this.commitOrRemove();
    const drawingEditor = this.currentLayer?.endDrawingSession(true);
    if (!this.hasSelection && !drawingEditor) {
      return;
    }
    const editors = drawingEditor ? [drawingEditor] : [...this.#selectedEditors];
    const cmd = () => {
      this._editorUndoBar?.show(undo, editors.length === 1 ? editors[0].editorType : editors.length);
      for (const editor of editors) {
        editor.remove();
      }
    };
    const undo = () => {
      for (const editor of editors) {
        this.#addEditorToLayer(editor);
      }
    };
    this.addCommands({
      cmd,
      undo,
      mustExec: true
    });
  }
  commitOrRemove() {
    this.#activeEditor?.commitOrRemove();
  }
  hasSomethingToControl() {
    return this.#activeEditor || this.hasSelection;
  }
  #selectEditors(editors) {
    for (const editor of this.#selectedEditors) {
      editor.unselect();
    }
    this.#selectedEditors.clear();
    for (const editor of editors) {
      if (editor.isEmpty()) {
        continue;
      }
      this.#selectedEditors.add(editor);
      editor.select();
    }
    this.#dispatchUpdateStates({
      hasSelectedEditor: this.hasSelection
    });
  }
  selectAll() {
    for (const editor of this.#selectedEditors) {
      editor.commit();
    }
    this.#selectEditors(this.#allEditors.values());
  }
  unselectAll() {
    if (this.#activeEditor) {
      this.#activeEditor.commitOrRemove();
      if (this.#mode !== AnnotationEditorType.NONE) {
        return;
      }
    }
    if (this.#currentDrawingSession?.commitOrRemove()) {
      return;
    }
    this.#commentManager?.destroyPopup();
    if (!this.hasSelection) {
      return;
    }
    for (const editor of this.#selectedEditors) {
      editor.unselect();
    }
    this.#selectedEditors.clear();
    this.#dispatchUpdateStates({
      hasSelectedEditor: false
    });
  }
  translateSelectedEditors(x, y, noCommit = false) {
    if (!noCommit) {
      this.commitOrRemove();
    }
    if (!this.hasSelection) {
      return;
    }
    this.#translation[0] += x;
    this.#translation[1] += y;
    const [totalX, totalY] = this.#translation;
    const editors = [...this.#selectedEditors];
    const TIME_TO_WAIT = 1000;
    if (this.#translationTimeoutId) {
      clearTimeout(this.#translationTimeoutId);
    }
    this.#translationTimeoutId = setTimeout(() => {
      this.#translationTimeoutId = null;
      this.#translation[0] = this.#translation[1] = 0;
      this.addCommands({
        cmd: () => {
          for (const editor of editors) {
            if (this.#allEditors.has(editor.id)) {
              editor.translateInPage(totalX, totalY);
              editor.translationDone();
            }
          }
        },
        undo: () => {
          for (const editor of editors) {
            if (this.#allEditors.has(editor.id)) {
              editor.translateInPage(-totalX, -totalY);
              editor.translationDone();
            }
          }
        },
        mustExec: false
      });
    }, TIME_TO_WAIT);
    for (const editor of editors) {
      editor.translateInPage(x, y);
      editor.translationDone();
    }
  }
  setUpDragSession() {
    if (!this.hasSelection) {
      return;
    }
    this.disableUserSelect(true);
    this.#draggingEditors = new Map();
    for (const editor of this.#selectedEditors) {
      this.#draggingEditors.set(editor, {
        savedX: editor.x,
        savedY: editor.y,
        savedPageIndex: editor.pageIndex,
        newX: 0,
        newY: 0,
        newPageIndex: -1
      });
    }
  }
  endDragSession() {
    if (!this.#draggingEditors) {
      return false;
    }
    this.disableUserSelect(false);
    const map = this.#draggingEditors;
    this.#draggingEditors = null;
    let mustBeAddedInUndoStack = false;
    for (const [{
      x,
      y,
      pageIndex
    }, value] of map) {
      value.newX = x;
      value.newY = y;
      value.newPageIndex = pageIndex;
      mustBeAddedInUndoStack ||= x !== value.savedX || y !== value.savedY || pageIndex !== value.savedPageIndex;
    }
    if (!mustBeAddedInUndoStack) {
      return false;
    }
    const move = (editor, x, y, pageIndex) => {
      if (this.#allEditors.has(editor.id)) {
        const parent = this.#allLayers.get(pageIndex);
        if (parent) {
          editor._setParentAndPosition(parent, x, y);
        } else {
          editor.pageIndex = pageIndex;
          editor.x = x;
          editor.y = y;
        }
      }
    };
    this.addCommands({
      cmd: () => {
        for (const [editor, {
          newX,
          newY,
          newPageIndex
        }] of map) {
          move(editor, newX, newY, newPageIndex);
        }
      },
      undo: () => {
        for (const [editor, {
          savedX,
          savedY,
          savedPageIndex
        }] of map) {
          move(editor, savedX, savedY, savedPageIndex);
        }
      },
      mustExec: true
    });
    return true;
  }
  dragSelectedEditors(tx, ty) {
    if (!this.#draggingEditors) {
      return;
    }
    for (const editor of this.#draggingEditors.keys()) {
      editor.drag(tx, ty);
    }
  }
  rebuild(editor) {
    if (editor.parent === null) {
      const parent = this.getLayer(editor.pageIndex);
      if (parent) {
        parent.changeParent(editor);
        parent.addOrRebuild(editor);
      } else {
        this.addEditor(editor);
        this.addToAnnotationStorage(editor);
        editor.rebuild();
      }
    } else {
      editor.parent.addOrRebuild(editor);
    }
  }
  get isEditorHandlingKeyboard() {
    return this.getActive()?.shouldGetKeyboardEvents() || this.#selectedEditors.size === 1 && this.firstSelectedEditor.shouldGetKeyboardEvents();
  }
  isActive(editor) {
    return this.#activeEditor === editor;
  }
  getActive() {
    return this.#activeEditor;
  }
  getMode() {
    return this.#mode;
  }
  isEditingMode() {
    return this.#mode !== AnnotationEditorType.NONE;
  }
  get imageManager() {
    return shadow(this, "imageManager", new ImageManager());
  }
  getSelectionBoxes(textLayer) {
    if (!textLayer) {
      return null;
    }
    const selection = document.getSelection();
    for (let i = 0, ii = selection.rangeCount; i < ii; i++) {
      if (!textLayer.contains(selection.getRangeAt(i).commonAncestorContainer)) {
        return null;
      }
    }
    const {
      x: layerX,
      y: layerY,
      width: parentWidth,
      height: parentHeight
    } = textLayer.getBoundingClientRect();
    let rotator;
    switch (textLayer.getAttribute("data-main-rotation")) {
      case "90":
        rotator = (x, y, w, h) => ({
          x: (y - layerY) / parentHeight,
          y: 1 - (x + w - layerX) / parentWidth,
          width: h / parentHeight,
          height: w / parentWidth
        });
        break;
      case "180":
        rotator = (x, y, w, h) => ({
          x: 1 - (x + w - layerX) / parentWidth,
          y: 1 - (y + h - layerY) / parentHeight,
          width: w / parentWidth,
          height: h / parentHeight
        });
        break;
      case "270":
        rotator = (x, y, w, h) => ({
          x: 1 - (y + h - layerY) / parentHeight,
          y: (x - layerX) / parentWidth,
          width: h / parentHeight,
          height: w / parentWidth
        });
        break;
      default:
        rotator = (x, y, w, h) => ({
          x: (x - layerX) / parentWidth,
          y: (y - layerY) / parentHeight,
          width: w / parentWidth,
          height: h / parentHeight
        });
        break;
    }
    const boxes = [];
    for (let i = 0, ii = selection.rangeCount; i < ii; i++) {
      const range = selection.getRangeAt(i);
      if (range.collapsed) {
        continue;
      }
      for (const {
        x,
        y,
        width,
        height
      } of range.getClientRects()) {
        if (width === 0 || height === 0) {
          continue;
        }
        boxes.push(rotator(x, y, width, height));
      }
    }
    return boxes.length === 0 ? null : boxes;
  }
  addChangedExistingAnnotation({
    annotationElementId,
    id
  }) {
    (this.#changedExistingAnnotations ||= new Map()).set(annotationElementId, id);
  }
  removeChangedExistingAnnotation({
    annotationElementId
  }) {
    this.#changedExistingAnnotations?.delete(annotationElementId);
  }
  renderAnnotationElement(annotation) {
    const editorId = this.#changedExistingAnnotations?.get(annotation.data.id);
    if (!editorId) {
      return;
    }
    const editor = this.#annotationStorage.getRawValue(editorId);
    if (!editor) {
      return;
    }
    if (this.#mode === AnnotationEditorType.NONE && !editor.hasBeenModified) {
      return;
    }
    editor.renderAnnotationElement(annotation);
  }
  setMissingCanvas(annotationId, annotationElementId, canvas) {
    const editor = this.#missingCanvases?.get(annotationId);
    if (!editor) {
      return;
    }
    editor.setCanvas(annotationElementId, canvas);
    this.#missingCanvases.delete(annotationId);
  }
  addMissingCanvas(annotationId, editor) {
    (this.#missingCanvases ||= new Map()).set(annotationId, editor);
  }
}

;// ./src/display/editor/alt_text.js

class AltText {
  #altText = null;
  #altTextDecorative = false;
  #altTextButton = null;
  #altTextButtonLabel = null;
  #altTextTooltip = null;
  #altTextTooltipTimeout = null;
  #altTextWasFromKeyBoard = false;
  #badge = null;
  #editor = null;
  #guessedText = null;
  #textWithDisclaimer = null;
  #useNewAltTextFlow = false;
  static #l10nNewButton = null;
  static _l10n = null;
  constructor(editor) {
    this.#editor = editor;
    this.#useNewAltTextFlow = editor._uiManager.useNewAltTextFlow;
    AltText.#l10nNewButton ||= Object.freeze({
      added: "pdfjs-editor-new-alt-text-added-button",
      "added-label": "pdfjs-editor-new-alt-text-added-button-label",
      missing: "pdfjs-editor-new-alt-text-missing-button",
      "missing-label": "pdfjs-editor-new-alt-text-missing-button-label",
      review: "pdfjs-editor-new-alt-text-to-review-button",
      "review-label": "pdfjs-editor-new-alt-text-to-review-button-label"
    });
  }
  static initialize(l10n) {
    AltText._l10n ??= l10n;
  }
  async render() {
    const altText = this.#altTextButton = document.createElement("button");
    altText.className = "altText";
    altText.tabIndex = "0";
    const label = this.#altTextButtonLabel = document.createElement("span");
    altText.append(label);
    if (this.#useNewAltTextFlow) {
      altText.classList.add("new");
      altText.setAttribute("data-l10n-id", AltText.#l10nNewButton.missing);
      label.setAttribute("data-l10n-id", AltText.#l10nNewButton["missing-label"]);
    } else {
      altText.setAttribute("data-l10n-id", "pdfjs-editor-alt-text-button");
      label.setAttribute("data-l10n-id", "pdfjs-editor-alt-text-button-label");
    }
    const signal = this.#editor._uiManager._signal;
    altText.addEventListener("contextmenu", noContextMenu, {
      signal
    });
    altText.addEventListener("pointerdown", event => event.stopPropagation(), {
      signal
    });
    const onClick = event => {
      event.preventDefault();
      this.#editor._uiManager.editAltText(this.#editor);
      if (this.#useNewAltTextFlow) {
        this.#editor._reportTelemetry({
          action: "pdfjs.image.alt_text.image_status_label_clicked",
          data: {
            label: this.#label
          }
        });
      }
    };
    altText.addEventListener("click", onClick, {
      capture: true,
      signal
    });
    altText.addEventListener("keydown", event => {
      if (event.target === altText && event.key === "Enter") {
        this.#altTextWasFromKeyBoard = true;
        onClick(event);
      }
    }, {
      signal
    });
    await this.#setState();
    return altText;
  }
  get #label() {
    return this.#altText && "added" || this.#altText === null && this.guessedText && "review" || "missing";
  }
  finish() {
    if (!this.#altTextButton) {
      return;
    }
    this.#altTextButton.focus({
      focusVisible: this.#altTextWasFromKeyBoard
    });
    this.#altTextWasFromKeyBoard = false;
  }
  isEmpty() {
    return this.#useNewAltTextFlow ? this.#altText === null : !this.#altText && !this.#altTextDecorative;
  }
  hasData() {
    return this.#useNewAltTextFlow ? this.#altText !== null || !!this.#guessedText : this.isEmpty();
  }
  get guessedText() {
    return this.#guessedText;
  }
  async setGuessedText(guessedText) {
    if (this.#altText !== null) {
      return;
    }
    this.#guessedText = guessedText;
    this.#textWithDisclaimer = await AltText._l10n.get("pdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer", {
      generatedAltText: guessedText
    });
    this.#setState();
  }
  toggleAltTextBadge(visibility = false) {
    if (!this.#useNewAltTextFlow || this.#altText) {
      this.#badge?.remove();
      this.#badge = null;
      return;
    }
    if (!this.#badge) {
      const badge = this.#badge = document.createElement("div");
      badge.className = "noAltTextBadge";
      this.#editor.div.append(badge);
    }
    this.#badge.classList.toggle("hidden", !visibility);
  }
  serialize(isForCopying) {
    let altText = this.#altText;
    if (!isForCopying && this.#guessedText === altText) {
      altText = this.#textWithDisclaimer;
    }
    return {
      altText,
      decorative: this.#altTextDecorative,
      guessedText: this.#guessedText,
      textWithDisclaimer: this.#textWithDisclaimer
    };
  }
  get data() {
    return {
      altText: this.#altText,
      decorative: this.#altTextDecorative
    };
  }
  set data({
    altText,
    decorative,
    guessedText,
    textWithDisclaimer,
    cancel = false
  }) {
    if (guessedText) {
      this.#guessedText = guessedText;
      this.#textWithDisclaimer = textWithDisclaimer;
    }
    if (this.#altText === altText && this.#altTextDecorative === decorative) {
      return;
    }
    if (!cancel) {
      this.#altText = altText;
      this.#altTextDecorative = decorative;
    }
    this.#setState();
  }
  toggle(enabled = false) {
    if (!this.#altTextButton) {
      return;
    }
    if (!enabled && this.#altTextTooltipTimeout) {
      clearTimeout(this.#altTextTooltipTimeout);
      this.#altTextTooltipTimeout = null;
    }
    this.#altTextButton.disabled = !enabled;
  }
  shown() {
    this.#editor._reportTelemetry({
      action: "pdfjs.image.alt_text.image_status_label_displayed",
      data: {
        label: this.#label
      }
    });
  }
  destroy() {
    this.#altTextButton?.remove();
    this.#altTextButton = null;
    this.#altTextButtonLabel = null;
    this.#altTextTooltip = null;
    this.#badge?.remove();
    this.#badge = null;
  }
  async #setState() {
    const button = this.#altTextButton;
    if (!button) {
      return;
    }
    if (this.#useNewAltTextFlow) {
      button.classList.toggle("done", !!this.#altText);
      button.setAttribute("data-l10n-id", AltText.#l10nNewButton[this.#label]);
      this.#altTextButtonLabel?.setAttribute("data-l10n-id", AltText.#l10nNewButton[`${this.#label}-label`]);
      if (!this.#altText) {
        this.#altTextTooltip?.remove();
        return;
      }
    } else {
      if (!this.#altText && !this.#altTextDecorative) {
        button.classList.remove("done");
        this.#altTextTooltip?.remove();
        return;
      }
      button.classList.add("done");
      button.setAttribute("data-l10n-id", "pdfjs-editor-alt-text-edit-button");
    }
    let tooltip = this.#altTextTooltip;
    if (!tooltip) {
      this.#altTextTooltip = tooltip = document.createElement("span");
      tooltip.className = "tooltip";
      tooltip.setAttribute("role", "tooltip");
      tooltip.id = `alt-text-tooltip-${this.#editor.id}`;
      const DELAY_TO_SHOW_TOOLTIP = 100;
      const signal = this.#editor._uiManager._signal;
      signal.addEventListener("abort", () => {
        clearTimeout(this.#altTextTooltipTimeout);
        this.#altTextTooltipTimeout = null;
      }, {
        once: true
      });
      button.addEventListener("mouseenter", () => {
        this.#altTextTooltipTimeout = setTimeout(() => {
          this.#altTextTooltipTimeout = null;
          this.#altTextTooltip.classList.add("show");
          this.#editor._reportTelemetry({
            action: "alt_text_tooltip"
          });
        }, DELAY_TO_SHOW_TOOLTIP);
      }, {
        signal
      });
      button.addEventListener("mouseleave", () => {
        if (this.#altTextTooltipTimeout) {
          clearTimeout(this.#altTextTooltipTimeout);
          this.#altTextTooltipTimeout = null;
        }
        this.#altTextTooltip?.classList.remove("show");
      }, {
        signal
      });
    }
    if (this.#altTextDecorative) {
      tooltip.setAttribute("data-l10n-id", "pdfjs-editor-alt-text-decorative-tooltip");
    } else {
      tooltip.removeAttribute("data-l10n-id");
      tooltip.textContent = this.#altText;
    }
    if (!tooltip.parentNode) {
      button.append(tooltip);
    }
    const element = this.#editor.getElementForAltText();
    element?.setAttribute("aria-describedby", tooltip.id);
  }
}

;// ./src/display/editor/comment.js

class Comment {
  #commentStandaloneButton = null;
  #commentToolbarButton = null;
  #commentWasFromKeyBoard = false;
  #editor = null;
  #initialText = null;
  #richText = null;
  #text = null;
  #date = null;
  #deleted = false;
  #popupPosition = null;
  constructor(editor) {
    this.#editor = editor;
  }
  renderForToolbar() {
    const button = this.#commentToolbarButton = document.createElement("button");
    button.className = "comment";
    return this.#render(button, false);
  }
  renderForStandalone() {
    const button = this.#commentStandaloneButton = document.createElement("button");
    button.className = "annotationCommentButton";
    const position = this.#editor.commentButtonPosition;
    if (position) {
      const {
        style
      } = button;
      style.insetInlineEnd = `calc(${100 * (this.#editor._uiManager.direction === "ltr" ? 1 - position[0] : position[0])}% - var(--comment-button-dim))`;
      style.top = `calc(${100 * position[1]}% - var(--comment-button-dim))`;
      const color = this.#editor.commentButtonColor;
      if (color) {
        style.backgroundColor = color;
      }
    }
    return this.#render(button, true);
  }
  focusButton() {
    setTimeout(() => {
      (this.#commentStandaloneButton ?? this.#commentToolbarButton)?.focus();
    }, 0);
  }
  onUpdatedColor() {
    if (!this.#commentStandaloneButton) {
      return;
    }
    const color = this.#editor.commentButtonColor;
    if (color) {
      this.#commentStandaloneButton.style.backgroundColor = color;
    }
    this.#editor._uiManager.updatePopupColor(this.#editor);
  }
  get commentButtonWidth() {
    return (this.#commentStandaloneButton?.getBoundingClientRect().width ?? 0) / this.#editor.parent.boundingClientRect.width;
  }
  get commentPopupPositionInLayer() {
    if (this.#popupPosition) {
      return this.#popupPosition;
    }
    if (!this.#commentStandaloneButton) {
      return null;
    }
    const {
      x,
      y,
      height
    } = this.#commentStandaloneButton.getBoundingClientRect();
    const {
      x: parentX,
      y: parentY,
      width: parentWidth,
      height: parentHeight
    } = this.#editor.parent.boundingClientRect;
    return [(x - parentX) / parentWidth, (y + height - parentY) / parentHeight];
  }
  set commentPopupPositionInLayer(pos) {
    this.#popupPosition = pos;
  }
  hasDefaultPopupPosition() {
    return this.#popupPosition === null;
  }
  removeStandaloneCommentButton() {
    this.#commentStandaloneButton?.remove();
    this.#commentStandaloneButton = null;
  }
  removeToolbarCommentButton() {
    this.#commentToolbarButton?.remove();
    this.#commentToolbarButton = null;
  }
  setCommentButtonStates({
    selected,
    hasPopup
  }) {
    if (!this.#commentStandaloneButton) {
      return;
    }
    this.#commentStandaloneButton.classList.toggle("selected", selected);
    this.#commentStandaloneButton.ariaExpanded = hasPopup;
  }
  #render(comment, isStandalone) {
    if (!this.#editor._uiManager.hasCommentManager()) {
      return null;
    }
    comment.tabIndex = "0";
    comment.ariaHasPopup = "dialog";
    if (isStandalone) {
      comment.ariaControls = "commentPopup";
      comment.setAttribute("data-l10n-id", "pdfjs-show-comment-button");
    } else {
      comment.ariaControlsElements = [this.#editor._uiManager.getCommentDialogElement()];
      comment.setAttribute("data-l10n-id", "pdfjs-editor-add-comment-button");
    }
    const signal = this.#editor._uiManager._signal;
    if (!(signal instanceof AbortSignal) || signal.aborted) {
      return comment;
    }
    comment.addEventListener("contextmenu", noContextMenu, {
      signal
    });
    if (isStandalone) {
      comment.addEventListener("focusin", e => {
        this.#editor._focusEventsAllowed = false;
        stopEvent(e);
      }, {
        capture: true,
        signal
      });
      comment.addEventListener("focusout", e => {
        this.#editor._focusEventsAllowed = true;
        stopEvent(e);
      }, {
        capture: true,
        signal
      });
    }
    comment.addEventListener("pointerdown", event => event.stopPropagation(), {
      signal
    });
    const onClick = event => {
      event.preventDefault();
      if (comment === this.#commentToolbarButton) {
        this.edit();
      } else {
        this.#editor.toggleComment(true);
      }
    };
    comment.addEventListener("click", onClick, {
      capture: true,
      signal
    });
    comment.addEventListener("keydown", event => {
      if (event.target === comment && event.key === "Enter") {
        this.#commentWasFromKeyBoard = true;
        onClick(event);
      }
    }, {
      signal
    });
    comment.addEventListener("pointerenter", () => {
      this.#editor.toggleComment(false, true);
    }, {
      signal
    });
    comment.addEventListener("pointerleave", () => {
      this.#editor.toggleComment(false, false);
    }, {
      signal
    });
    return comment;
  }
  edit(options) {
    const position = this.commentPopupPositionInLayer;
    let posX, posY;
    if (position) {
      [posX, posY] = position;
    } else {
      [posX, posY] = this.#editor.commentButtonPosition;
      const {
        width,
        height,
        x,
        y
      } = this.#editor;
      posX = x + posX * width;
      posY = y + posY * height;
    }
    const parentDimensions = this.#editor.parent.boundingClientRect;
    const {
      x: parentX,
      y: parentY,
      width: parentWidth,
      height: parentHeight
    } = parentDimensions;
    this.#editor._uiManager.editComment(this.#editor, parentX + posX * parentWidth, parentY + posY * parentHeight, {
      ...options,
      parentDimensions
    });
  }
  finish() {
    if (!this.#commentToolbarButton) {
      return;
    }
    this.#commentToolbarButton.focus({
      focusVisible: this.#commentWasFromKeyBoard
    });
    this.#commentWasFromKeyBoard = false;
  }
  isDeleted() {
    return this.#deleted || this.#text === "";
  }
  isEmpty() {
    return this.#text === null;
  }
  hasBeenEdited() {
    return this.isDeleted() || this.#text !== this.#initialText;
  }
  serialize() {
    return this.data;
  }
  get data() {
    return {
      text: this.#text,
      richText: this.#richText,
      date: this.#date,
      deleted: this.isDeleted()
    };
  }
  set data(text) {
    if (text !== this.#text) {
      this.#richText = null;
    }
    if (text === null) {
      this.#text = "";
      this.#deleted = true;
      return;
    }
    this.#text = text;
    this.#date = new Date();
    this.#deleted = false;
  }
  restoreData({
    text,
    richText,
    date
  }) {
    this.#text = text;
    this.#richText = richText;
    this.#date = date;
    this.#deleted = false;
  }
  setInitialText(text, richText = null) {
    this.#initialText = text;
    this.data = text;
    this.#date = null;
    this.#richText = richText;
  }
  shown() {}
  destroy() {
    this.#commentToolbarButton?.remove();
    this.#commentToolbarButton = null;
    this.#commentStandaloneButton?.remove();
    this.#commentStandaloneButton = null;
    this.#text = "";
    this.#richText = null;
    this.#date = null;
    this.#editor = null;
    this.#commentWasFromKeyBoard = false;
    this.#deleted = false;
  }
}

;// ./src/display/touch_manager.js


function preventDefault(evt) {
  evt.preventDefault();
}
const MIN_TOUCH_SPAN = 1e-4;
function stopTouchEvent(evt) {
  if (evt.cancelable) {
    stopEvent(evt);
    return true;
  }
  evt.stopPropagation();
  return false;
}
class TouchManager {
  #container;
  #isPinching = false;
  #isPinchingStopped = null;
  #isPinchingDisabled;
  #onPinchStart;
  #onPinching;
  #onPinchEnd;
  #onPanning;
  #ownsGesture = false;
  #pointerDownAC = null;
  #signal;
  #touchIds = new Set();
  #touchInfo = null;
  #touchManagerAC;
  #touchMoveAC = null;
  #unconfirmedPinch = 0;
  constructor({
    container,
    isPinchingDisabled = null,
    isPinchingStopped = null,
    onPinchStart = null,
    onPinching = null,
    onPinchEnd = null,
    onPanning = null,
    signal
  }) {
    this.#container = container;
    this.#isPinchingStopped = isPinchingStopped;
    this.#isPinchingDisabled = isPinchingDisabled;
    this.#onPinchStart = onPinchStart;
    this.#onPinching = onPinching;
    this.#onPinchEnd = onPinchEnd;
    this.#onPanning = onPanning;
    this.#touchManagerAC = new AbortController();
    this.#signal = AbortSignal.any([signal, this.#touchManagerAC.signal]);
    container.addEventListener("touchstart", this.#onTouchStart.bind(this), {
      passive: false,
      signal: this.#signal
    });
  }
  get MIN_TOUCH_DISTANCE_TO_PINCH() {
    return 35 / OutputScale.pixelRatio;
  }
  get MIN_TOUCH_DISTANCE_TO_SCALE() {
    return 4 / OutputScale.pixelRatio;
  }
  #onTouchStart(evt) {
    if (this.#isPinchingDisabled?.()) {
      return;
    }
    this.#pruneTouchIds(evt);
    const touchIds = this.#touchIds;
    for (const {
      identifier
    } of evt.changedTouches) {
      touchIds.add(identifier);
    }
    if (touchIds.size === 1) {
      this.#armPointerDown();
      return;
    }
    if (!this.#touchMoveAC) {
      this.#touchMoveAC = new AbortController();
      const signal = AbortSignal.any([this.#signal, this.#touchMoveAC.signal]);
      const container = this.#container;
      const opt = {
        signal,
        capture: false,
        passive: false
      };
      container.addEventListener("touchmove", this.#onTouchMove.bind(this), opt);
      const onTouchEnd = this.#onTouchEnd.bind(this);
      container.addEventListener("touchend", onTouchEnd, opt);
      container.addEventListener("touchcancel", onTouchEnd, opt);
      opt.capture = true;
      container.addEventListener("pointerdown", stopEvent, opt);
      container.addEventListener("pointermove", stopEvent, opt);
      container.addEventListener("pointercancel", preventDefault, opt);
      container.addEventListener("pointerup", preventDefault, opt);
      this.#onPinchStart?.();
    }
    this.#ownsGesture = stopTouchEvent(evt);
    this.#setTouchInfo(evt);
  }
  #armPointerDown() {
    if (this.#pointerDownAC) {
      return;
    }
    const pointerDownAC = this.#pointerDownAC = new AbortController();
    const signal = AbortSignal.any([this.#signal, pointerDownAC.signal]);
    const container = this.#container;
    const opts = {
      capture: true,
      signal,
      passive: false
    };
    const cancelPointerDown = e => {
      if (e.pointerType === "touch") {
        this.#pointerDownAC?.abort();
        this.#pointerDownAC = null;
      }
    };
    container.addEventListener("pointerdown", e => {
      if (e.pointerType === "touch") {
        stopEvent(e);
        cancelPointerDown(e);
      }
    }, opts);
    container.addEventListener("pointerup", cancelPointerDown, opts);
    container.addEventListener("pointercancel", cancelPointerDown, opts);
  }
  #pruneTouchIds(evt) {
    const previous = this.#touchIds;
    if (previous.size === 0) {
      return;
    }
    const touchIds = this.#touchIds = new Set();
    for (const {
      identifier
    } of evt.touches) {
      if (previous.has(identifier)) {
        touchIds.add(identifier);
      }
    }
  }
  #getTrackedTouches(evt) {
    const touchIds = this.#touchIds;
    const touches = [];
    for (const touch of evt.touches) {
      if (touchIds.has(touch.identifier)) {
        touches.push(touch);
      }
    }
    return touches;
  }
  #setTouchInfo(evt) {
    const touches = this.#getTrackedTouches(evt);
    if (touches.length !== 2 || this.#isPinchingStopped?.()) {
      this.#touchInfo = null;
      return;
    }
    const [touch0, touch1] = touches;
    this.#touchInfo = {
      touch0X: touch0.screenX,
      touch0Y: touch0.screenY,
      touch1X: touch1.screenX,
      touch1Y: touch1.screenY,
      panX: (touch0.clientX + touch1.clientX) / 2,
      panY: (touch0.clientY + touch1.clientY) / 2,
      screenPanX: (touch0.screenX + touch1.screenX) / 2,
      screenPanY: (touch0.screenY + touch1.screenY) / 2
    };
  }
  #onTouchMove(evt) {
    if (!this.#touchInfo) {
      return;
    }
    const touches = this.#getTrackedTouches(evt);
    if (touches.length !== 2) {
      return;
    }
    const wasOwned = this.#ownsGesture;
    this.#ownsGesture = stopTouchEvent(evt);
    if (!this.#ownsGesture) {
      return;
    }
    if (!wasOwned) {
      this.#setTouchInfo(evt);
      return;
    }
    const [touch0, touch1] = touches;
    const {
      screenX: screen0X,
      screenY: screen0Y
    } = touch0;
    const {
      screenX: screen1X,
      screenY: screen1Y
    } = touch1;
    const touchInfo = this.#touchInfo;
    const {
      touch0X: pTouch0X,
      touch0Y: pTouch0Y,
      touch1X: pTouch1X,
      touch1Y: pTouch1Y,
      panX: pPanX,
      panY: pPanY
    } = touchInfo;
    const prevGapX = pTouch1X - pTouch0X;
    const prevGapY = pTouch1Y - pTouch0Y;
    const currGapX = screen1X - screen0X;
    const currGapY = screen1Y - screen0Y;
    const panX = (touch0.clientX + touch1.clientX) / 2;
    const panY = (touch0.clientY + touch1.clientY) / 2;
    touchInfo.panX = panX;
    touchInfo.panY = panY;
    const dx = panX - pPanX;
    const dy = panY - pPanY;
    const screenPanX = (screen0X + screen1X) / 2;
    const screenPanY = (screen0Y + screen1Y) / 2;
    const translation = Math.hypot(screenPanX - touchInfo.screenPanX, screenPanY - touchInfo.screenPanY);
    touchInfo.screenPanX = screenPanX;
    touchInfo.screenPanY = screenPanY;
    const distance = Math.hypot(currGapX, currGapY);
    const pDistance = Math.hypot(prevGapX, prevGapY);
    const minDistance = this.#isPinching ? this.MIN_TOUCH_DISTANCE_TO_SCALE : this.MIN_TOUCH_DISTANCE_TO_PINCH + 2 * translation;
    if (distance < MIN_TOUCH_SPAN || pDistance < MIN_TOUCH_SPAN || Math.abs(pDistance - distance) <= minDistance) {
      if (dx || dy) {
        this.#onPanning?.(dx, dy);
      }
      return;
    }
    touchInfo.touch0X = screen0X;
    touchInfo.touch0Y = screen0Y;
    touchInfo.touch1X = screen1X;
    touchInfo.touch1Y = screen1Y;
    const direction = Math.sign(distance - pDistance);
    if (!this.#isPinching) {
      this.#isPinching = true;
      this.#unconfirmedPinch = direction;
      if (dx || dy) {
        this.#onPanning?.(dx, dy);
      }
      return;
    }
    if (this.#unconfirmedPinch) {
      const unconfirmed = this.#unconfirmedPinch;
      this.#unconfirmedPinch = 0;
      if (direction !== unconfirmed && Math.abs(distance - pDistance) <= 2 * translation) {
        this.#isPinching = false;
        if (dx || dy) {
          this.#onPanning?.(dx, dy);
        }
        return;
      }
    }
    this.#onPinching?.([pPanX, pPanY], pDistance, distance, dx, dy);
  }
  #onTouchEnd(evt) {
    this.#pruneTouchIds(evt);
    if (this.#touchIds.size >= 2) {
      this.#setTouchInfo(evt);
      return;
    }
    const wasTracking = !!this.#touchInfo;
    this.#endGesture();
    if (this.#touchIds.size === 1) {
      this.#armPointerDown();
    }
    if (wasTracking) {
      stopTouchEvent(evt);
    }
  }
  #endGesture() {
    this.#touchInfo = null;
    this.#isPinching = false;
    this.#unconfirmedPinch = 0;
    this.#ownsGesture = false;
    if (this.#touchMoveAC) {
      this.#touchMoveAC.abort();
      this.#touchMoveAC = null;
      this.#onPinchEnd?.();
    }
  }
  destroy() {
    this.#endGesture();
    this.#touchIds.clear();
    this.#touchManagerAC?.abort();
    this.#touchManagerAC = null;
    this.#pointerDownAC?.abort();
    this.#pointerDownAC = null;
  }
}

;// ./src/display/editor/editor.js








class AnnotationEditor {
  #accessibilityData = null;
  #allResizerDivs = null;
  #altText = null;
  #comment = null;
  #commentStandaloneButton = null;
  #disabled = false;
  #dragPointerId = null;
  #dragPointerType = "";
  #resizersDiv = null;
  #lastPointerCoords = null;
  #savedDimensions = null;
  #fakeAnnotation = null;
  #focusAC = null;
  #focusedResizerName = "";
  #hasBeenClicked = false;
  #initialRect = null;
  #isEditing = false;
  #isInEditMode = false;
  #isResizerEnabledForKeyboard = false;
  #moveInDOMTimeout = null;
  #prevDragX = 0;
  #prevDragY = 0;
  #telemetryTimeouts = null;
  #touchManager = null;
  isSelected = false;
  _isCopy = false;
  _editToolbar = null;
  _initialOptions = Object.create(null);
  _initialData = null;
  _isVisible = true;
  _uiManager = null;
  _focusEventsAllowed = true;
  static _l10n = null;
  static _l10nAlert = null;
  static _l10nResizer = null;
  #isDraggable = false;
  #zIndex = AnnotationEditor._zIndex++;
  static _borderLineWidth = -1;
  static _colorManager = new ColorManager();
  static _zIndex = 1;
  static _telemetryTimeout = 1000;
  static get _resizerKeyboardManager() {
    const resize = AnnotationEditor.prototype._resizeWithKeyboard;
    const small = AnnotationEditorUIManager.TRANSLATE_SMALL;
    const big = AnnotationEditorUIManager.TRANSLATE_BIG;
    return shadow(this, "_resizerKeyboardManager", new KeyboardManager([[["ArrowLeft"], resize, {
      args: [-small, 0]
    }], [["ctrl+ArrowLeft", "mac+shift+ArrowLeft"], resize, {
      args: [-big, 0]
    }], [["ArrowRight"], resize, {
      args: [small, 0]
    }], [["ctrl+ArrowRight", "mac+shift+ArrowRight"], resize, {
      args: [big, 0]
    }], [["ArrowUp"], resize, {
      args: [0, -small]
    }], [["ctrl+ArrowUp", "mac+shift+ArrowUp"], resize, {
      args: [0, -big]
    }], [["ArrowDown"], resize, {
      args: [0, small]
    }], [["ctrl+ArrowDown", "mac+shift+ArrowDown"], resize, {
      args: [0, big]
    }], [["Escape"], AnnotationEditor.prototype._stopResizingWithKeyboard]]));
  }
  constructor(parameters) {
    this.parent = parameters.parent;
    this.id = parameters.id;
    this.width = this.height = null;
    this.pageIndex = parameters.parent.pageIndex;
    this.name = parameters.name;
    this.div = null;
    this._uiManager = parameters.uiManager;
    this.annotationElementId = null;
    this._willKeepAspectRatio = false;
    this._initialOptions.isCentered = parameters.isCentered;
    this._structTreeParentId = null;
    this.annotationElementId = parameters.annotationElementId || null;
    this.creationDate = parameters.creationDate || new Date();
    this.modificationDate = parameters.modificationDate || null;
    this.canAddComment = true;
    const {
      rotation,
      rawDims: {
        pageWidth,
        pageHeight,
        pageX,
        pageY
      }
    } = this.parent.viewport;
    this.rotation = rotation;
    this.pageRotation = (360 + rotation - this._uiManager.viewParameters.rotation) % 360;
    this.pageDimensions = [pageWidth, pageHeight];
    this.pageTranslation = [pageX, pageY];
    const [width, height] = this.parentDimensions;
    this.x = parameters.x / width;
    this.y = parameters.y / height;
    this.isAttachedToDOM = false;
    this.deleted = false;
  }
  updatePageIndex(newPageIndex) {
    this.pageIndex = newPageIndex;
  }
  get editorType() {
    return Object.getPrototypeOf(this).constructor._type;
  }
  get mode() {
    return Object.getPrototypeOf(this).constructor._editorType;
  }
  static get isDrawer() {
    return false;
  }
  static get _defaultLineColor() {
    return shadow(this, "_defaultLineColor", this._colorManager.getHexCode("CanvasText"));
  }
  static deleteAnnotationElement(editor) {
    const fakeEditor = new FakeEditor({
      id: editor._uiManager.getId(),
      parent: editor.parent,
      uiManager: editor._uiManager
    });
    fakeEditor.annotationElementId = editor.annotationElementId;
    fakeEditor.deleted = true;
    fakeEditor._uiManager.addToAnnotationStorage(fakeEditor);
  }
  static initialize(l10n, _uiManager) {
    AnnotationEditor._l10n ??= l10n;
    AnnotationEditor._l10nAlert ??= Object.freeze({
      highlight: "pdfjs-editor-highlight-added-alert",
      freetext: "pdfjs-editor-freetext-added-alert",
      ink: "pdfjs-editor-ink-added-alert",
      stamp: "pdfjs-editor-stamp-added-alert",
      signature: "pdfjs-editor-signature-added-alert"
    });
    AnnotationEditor._l10nResizer ??= Object.freeze({
      topLeft: "pdfjs-editor-resizer-top-left",
      topMiddle: "pdfjs-editor-resizer-top-middle",
      topRight: "pdfjs-editor-resizer-top-right",
      middleRight: "pdfjs-editor-resizer-middle-right",
      bottomRight: "pdfjs-editor-resizer-bottom-right",
      bottomMiddle: "pdfjs-editor-resizer-bottom-middle",
      bottomLeft: "pdfjs-editor-resizer-bottom-left",
      middleLeft: "pdfjs-editor-resizer-middle-left"
    });
    if (AnnotationEditor._borderLineWidth !== -1) {
      return;
    }
    const style = getComputedStyle(document.documentElement);
    AnnotationEditor._borderLineWidth = parseFloat(style.getPropertyValue("--outline-width")) || 0;
  }
  static updateDefaultParams(_type, _value) {}
  static get defaultPropertiesToUpdate() {
    return [];
  }
  static isHandlingMimeForPasting(mime) {
    return false;
  }
  static paste(item, parent) {
    unreachable("Not implemented");
  }
  get propertiesToUpdate() {
    return [];
  }
  get _isDraggable() {
    return this.#isDraggable;
  }
  set _isDraggable(value) {
    this.#isDraggable = value;
    this.div?.classList.toggle("draggable", value);
  }
  get uid() {
    return this.annotationElementId || this.id;
  }
  get isEnterHandled() {
    return true;
  }
  center() {
    const [pageWidth, pageHeight] = this.pageDimensions;
    switch (this.parentRotation) {
      case 90:
        this.x -= this.height * pageHeight / (pageWidth * 2);
        this.y += this.width * pageWidth / (pageHeight * 2);
        break;
      case 180:
        this.x += this.width / 2;
        this.y += this.height / 2;
        break;
      case 270:
        this.x += this.height * pageHeight / (pageWidth * 2);
        this.y -= this.width * pageWidth / (pageHeight * 2);
        break;
      default:
        this.x -= this.width / 2;
        this.y -= this.height / 2;
        break;
    }
    this.fixAndSetPosition();
  }
  addCommands(params) {
    this._uiManager.addCommands(params);
  }
  get currentLayer() {
    return this._uiManager.currentLayer;
  }
  setInBackground() {
    this.div.style.zIndex = 0;
  }
  setInForeground() {
    this.div.style.zIndex = this.#zIndex;
  }
  setParent(parent) {
    if (parent !== null) {
      this.pageIndex = parent.pageIndex;
      this.pageDimensions = parent.pageDimensions;
    } else {
      this.#stopResizing();
      this.#fakeAnnotation?.remove();
      this.#fakeAnnotation = null;
    }
    this.parent = parent;
  }
  focusin(event) {
    if (!this._focusEventsAllowed) {
      return;
    }
    if (!this.#hasBeenClicked) {
      this.parent.setSelected(this);
    } else {
      this.#hasBeenClicked = false;
    }
  }
  focusout(event) {
    if (!this._focusEventsAllowed || !this.isAttachedToDOM) {
      return;
    }
    const target = event.relatedTarget;
    if (target?.closest(`#${this.id}`)) {
      return;
    }
    event.preventDefault();
    if (!this.parent?.isMultipleSelection) {
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
    if (!this.isInEditMode()) {
      return;
    }
    this.addToAnnotationStorage();
  }
  addToAnnotationStorage() {
    this._uiManager.addToAnnotationStorage(this);
  }
  setAt(x, y, tx, ty) {
    const [width, height] = this.parentDimensions;
    [tx, ty] = this.screenToPageTranslation(tx, ty);
    this.x = (x + tx) / width;
    this.y = (y + ty) / height;
    this.fixAndSetPosition();
  }
  _moveAfterPaste(baseX, baseY) {
    if (this.isClone) {
      delete this.isClone;
      return;
    }
    const [parentWidth, parentHeight] = this.parentDimensions;
    this.setAt(baseX * parentWidth, baseY * parentHeight, this.width * parentWidth, this.height * parentHeight);
    this._onTranslated();
  }
  #translate([width, height], x, y) {
    [x, y] = this.screenToPageTranslation(x, y);
    this.x += x / width;
    this.y += y / height;
    this._onTranslating(this.x, this.y);
    this.fixAndSetPosition();
  }
  translate(x, y) {
    this.#translate(this.parentDimensions, x, y);
  }
  translateInPage(x, y) {
    this.#initialRect ||= [this.x, this.y, this.width, this.height];
    this.#translate(this.pageDimensions, x, y);
    this.div.scrollIntoView({
      block: "nearest"
    });
  }
  translationDone() {
    this._onTranslated(this.x, this.y);
  }
  drag(tx, ty) {
    this.#initialRect ||= [this.x, this.y, this.width, this.height];
    const {
      div,
      parentDimensions: [parentWidth, parentHeight]
    } = this;
    this.x += tx / parentWidth;
    this.y += ty / parentHeight;
    if (this.parent && (this.x < 0 || this.x > 1 || this.y < 0 || this.y > 1)) {
      const {
        x,
        y
      } = this.div.getBoundingClientRect();
      if (this.parent.findNewParent(this, x, y)) {
        this.x -= Math.floor(this.x);
        this.y -= Math.floor(this.y);
      }
    }
    let {
      x,
      y
    } = this;
    const [bx, by] = this.getBaseTranslation();
    x += bx;
    y += by;
    const {
      style
    } = div;
    style.left = `${(100 * x).toFixed(2)}%`;
    style.top = `${(100 * y).toFixed(2)}%`;
    this._onTranslating(x, y);
  }
  _onTranslating(x, y) {}
  _onTranslated(x, y) {}
  get _hasBeenMoved() {
    return !!this.#initialRect && (this.#initialRect[0] !== this.x || this.#initialRect[1] !== this.y);
  }
  get _hasBeenResized() {
    return !!this.#initialRect && (this.#initialRect[2] !== this.width || this.#initialRect[3] !== this.height);
  }
  getBaseTranslation() {
    const [parentWidth, parentHeight] = this.parentDimensions;
    const {
      _borderLineWidth
    } = AnnotationEditor;
    const x = _borderLineWidth / parentWidth;
    const y = _borderLineWidth / parentHeight;
    switch (this.rotation) {
      case 90:
        return [-x, y];
      case 180:
        return [x, y];
      case 270:
        return [x, -y];
      default:
        return [-x, -y];
    }
  }
  get _mustFixPosition() {
    return true;
  }
  fixAndSetPosition(rotation = this.rotation) {
    const {
      div: {
        style
      },
      pageDimensions: [pageWidth, pageHeight]
    } = this;
    let {
      x,
      y,
      width,
      height
    } = this;
    width *= pageWidth;
    height *= pageHeight;
    x *= pageWidth;
    y *= pageHeight;
    let tx = 0;
    let ty = 0;
    const toolbar = this._uiManager._keepToolbarInPage && this._editToolbar?.div;
    if (toolbar?.offsetParent) {
      const scale = this.parentScale;
      const toolbarLeft = toolbar.offsetLeft + this.div.clientLeft;
      const toolbarTop = toolbar.offsetTop + this.div.clientTop;
      const left = Math.min(0, toolbarLeft) / scale;
      const top = Math.min(0, toolbarTop) / scale;
      const widthWithToolbar = width - left + Math.max(0, toolbarLeft + toolbar.offsetWidth - this.div.offsetWidth) / scale;
      const heightWithToolbar = height - top + Math.max(0, toolbarTop + toolbar.offsetHeight - this.div.offsetHeight) / scale;
      if (widthWithToolbar <= (rotation % 180 ? pageHeight : pageWidth)) {
        width = widthWithToolbar;
        tx = left;
      }
      if (heightWithToolbar <= (rotation % 180 ? pageWidth : pageHeight)) {
        height = heightWithToolbar;
        ty = top;
      }
      [tx, ty] = AnnotationEditor.#rotatePoint(tx, ty, rotation);
      x += tx;
      y += ty;
    }
    if (this._mustFixPosition) {
      switch (rotation) {
        case 0:
          x = MathClamp(x, 0, pageWidth - width);
          y = MathClamp(y, 0, pageHeight - height);
          break;
        case 90:
          x = MathClamp(x, 0, pageWidth - height);
          y = MathClamp(y, width, pageHeight);
          break;
        case 180:
          x = MathClamp(x, width, pageWidth);
          y = MathClamp(y, height, pageHeight);
          break;
        case 270:
          x = MathClamp(x, height, pageWidth);
          y = MathClamp(y, 0, pageHeight - width);
          break;
      }
    }
    this.x = x = (x - tx) / pageWidth;
    this.y = y = (y - ty) / pageHeight;
    const [bx, by] = this.getBaseTranslation();
    x += bx;
    y += by;
    style.left = `${(100 * x).toFixed(2)}%`;
    style.top = `${(100 * y).toFixed(2)}%`;
    this.moveInDOM();
  }
  static #rotatePoint(x, y, angle) {
    switch (angle) {
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
  screenToPageTranslation(x, y) {
    return AnnotationEditor.#rotatePoint(x, y, this.parentRotation);
  }
  pageTranslationToScreen(x, y) {
    return AnnotationEditor.#rotatePoint(x, y, 360 - this.parentRotation);
  }
  #getRotationMatrix(rotation) {
    switch (rotation) {
      case 90:
        {
          const [pageWidth, pageHeight] = this.pageDimensions;
          return [0, -pageWidth / pageHeight, pageHeight / pageWidth, 0];
        }
      case 180:
        return [-1, 0, 0, -1];
      case 270:
        {
          const [pageWidth, pageHeight] = this.pageDimensions;
          return [0, pageWidth / pageHeight, -pageHeight / pageWidth, 0];
        }
      default:
        return [1, 0, 0, 1];
    }
  }
  get parentScale() {
    return this._uiManager.viewParameters.realScale;
  }
  get parentRotation() {
    return (this._uiManager.viewParameters.rotation + this.pageRotation) % 360;
  }
  get parentDimensions() {
    const {
      parentScale,
      pageDimensions: [pageWidth, pageHeight]
    } = this;
    return [pageWidth * parentScale, pageHeight * parentScale];
  }
  setDims() {
    const {
      div: {
        style
      },
      width,
      height
    } = this;
    style.width = `${(100 * width).toFixed(2)}%`;
    style.height = `${(100 * height).toFixed(2)}%`;
  }
  getInitialTranslation() {
    return [0, 0];
  }
  #createResizers() {
    if (this.#resizersDiv) {
      return;
    }
    this.#resizersDiv = document.createElement("div");
    this.#resizersDiv.classList.add("resizers");
    const classes = this._willKeepAspectRatio ? ["topLeft", "topRight", "bottomRight", "bottomLeft"] : ["topLeft", "topMiddle", "topRight", "middleRight", "bottomRight", "bottomMiddle", "bottomLeft", "middleLeft"];
    const signal = this._uiManager._signal;
    for (const name of classes) {
      const div = document.createElement("div");
      this.#resizersDiv.append(div);
      div.classList.add("resizer", name);
      div.setAttribute("data-resizer-name", name);
      div.addEventListener("pointerdown", this.#resizerPointerdown.bind(this, name), {
        signal
      });
      div.addEventListener("contextmenu", noContextMenu, {
        signal
      });
      div.tabIndex = -1;
    }
    this.div.prepend(this.#resizersDiv);
  }
  #resizerPointerdown(name, event) {
    event.preventDefault();
    const {
      isMac
    } = FeatureTest.platform;
    if (event.button !== 0 || event.ctrlKey && isMac) {
      return;
    }
    this.#altText?.toggle(false);
    const savedDraggable = this._isDraggable;
    this._isDraggable = false;
    this.#lastPointerCoords = [event.screenX, event.screenY];
    const ac = new AbortController();
    const signal = this._uiManager.combinedSignal(ac);
    this.parent.togglePointerEvents(false);
    window.addEventListener("pointermove", this.#resizerPointermove.bind(this, name), {
      passive: true,
      capture: true,
      signal
    });
    window.addEventListener("touchmove", stopEvent, {
      passive: false,
      signal
    });
    window.addEventListener("contextmenu", noContextMenu, {
      signal
    });
    this.#savedDimensions = {
      savedX: this.x,
      savedY: this.y,
      savedWidth: this.width,
      savedHeight: this.height
    };
    const savedParentCursor = this.parent.div.style.cursor;
    const savedCursor = this.div.style.cursor;
    this.div.style.cursor = this.parent.div.style.cursor = window.getComputedStyle(event.target).cursor;
    const pointerUpCallback = () => {
      ac.abort();
      this.parent.togglePointerEvents(true);
      this.#altText?.toggle(true);
      this._isDraggable = savedDraggable;
      this.parent.div.style.cursor = savedParentCursor;
      this.div.style.cursor = savedCursor;
      this.#addResizeToUndoStack();
    };
    window.addEventListener("pointerup", pointerUpCallback, {
      signal
    });
    window.addEventListener("blur", pointerUpCallback, {
      signal
    });
  }
  #resize(x, y, width, height) {
    this.width = width;
    this.height = height;
    this.x = x;
    this.y = y;
    this.setDims();
    this.fixAndSetPosition();
    this._onResized();
  }
  _onResized() {}
  #addResizeToUndoStack() {
    if (!this.#savedDimensions) {
      return;
    }
    const {
      savedX,
      savedY,
      savedWidth,
      savedHeight
    } = this.#savedDimensions;
    this.#savedDimensions = null;
    const newX = this.x;
    const newY = this.y;
    const newWidth = this.width;
    const newHeight = this.height;
    if (newX === savedX && newY === savedY && newWidth === savedWidth && newHeight === savedHeight) {
      return;
    }
    this.addCommands({
      cmd: this.#resize.bind(this, newX, newY, newWidth, newHeight),
      undo: this.#resize.bind(this, savedX, savedY, savedWidth, savedHeight),
      mustExec: true
    });
  }
  static _round(x) {
    return Math.round(x * 10000) / 10000;
  }
  #resizerPointermove(name, event) {
    const [parentWidth, parentHeight] = this.parentDimensions;
    const savedX = this.x;
    const savedY = this.y;
    const savedWidth = this.width;
    const savedHeight = this.height;
    const minWidth = AnnotationEditor.MIN_SIZE / parentWidth;
    const minHeight = AnnotationEditor.MIN_SIZE / parentHeight;
    const rotationMatrix = this.#getRotationMatrix(this.rotation);
    const transf = (x, y) => [rotationMatrix[0] * x + rotationMatrix[2] * y, rotationMatrix[1] * x + rotationMatrix[3] * y];
    const invRotationMatrix = this.#getRotationMatrix(360 - this.rotation);
    const invTransf = (x, y) => [invRotationMatrix[0] * x + invRotationMatrix[2] * y, invRotationMatrix[1] * x + invRotationMatrix[3] * y];
    let getPoint;
    let getOpposite;
    let isDiagonal = false;
    let isHorizontal = false;
    switch (name) {
      case "topLeft":
        isDiagonal = true;
        getPoint = (w, h) => [0, 0];
        getOpposite = (w, h) => [w, h];
        break;
      case "topMiddle":
        getPoint = (w, h) => [w / 2, 0];
        getOpposite = (w, h) => [w / 2, h];
        break;
      case "topRight":
        isDiagonal = true;
        getPoint = (w, h) => [w, 0];
        getOpposite = (w, h) => [0, h];
        break;
      case "middleRight":
        isHorizontal = true;
        getPoint = (w, h) => [w, h / 2];
        getOpposite = (w, h) => [0, h / 2];
        break;
      case "bottomRight":
        isDiagonal = true;
        getPoint = (w, h) => [w, h];
        getOpposite = (w, h) => [0, 0];
        break;
      case "bottomMiddle":
        getPoint = (w, h) => [w / 2, h];
        getOpposite = (w, h) => [w / 2, 0];
        break;
      case "bottomLeft":
        isDiagonal = true;
        getPoint = (w, h) => [0, h];
        getOpposite = (w, h) => [w, 0];
        break;
      case "middleLeft":
        isHorizontal = true;
        getPoint = (w, h) => [0, h / 2];
        getOpposite = (w, h) => [w, h / 2];
        break;
    }
    const point = getPoint(savedWidth, savedHeight);
    const oppositePoint = getOpposite(savedWidth, savedHeight);
    let transfOppositePoint = transf(...oppositePoint);
    const oppositeX = AnnotationEditor._round(savedX + transfOppositePoint[0]);
    const oppositeY = AnnotationEditor._round(savedY + transfOppositePoint[1]);
    let ratioX = 1;
    let ratioY = 1;
    let deltaX, deltaY;
    if (!event.fromKeyboard) {
      const {
        screenX,
        screenY
      } = event;
      const [lastScreenX, lastScreenY] = this.#lastPointerCoords;
      [deltaX, deltaY] = this.screenToPageTranslation(screenX - lastScreenX, screenY - lastScreenY);
      this.#lastPointerCoords[0] = screenX;
      this.#lastPointerCoords[1] = screenY;
    } else {
      ({
        deltaX,
        deltaY
      } = event);
    }
    [deltaX, deltaY] = invTransf(deltaX / parentWidth, deltaY / parentHeight);
    if (isDiagonal) {
      const oldDiag = Math.hypot(savedWidth, savedHeight);
      ratioX = ratioY = Math.max(Math.min(Math.hypot(oppositePoint[0] - point[0] - deltaX, oppositePoint[1] - point[1] - deltaY) / oldDiag, 1 / savedWidth, 1 / savedHeight), minWidth / savedWidth, minHeight / savedHeight);
    } else if (isHorizontal) {
      ratioX = MathClamp(Math.abs(oppositePoint[0] - point[0] - deltaX), minWidth, 1) / savedWidth;
    } else {
      ratioY = MathClamp(Math.abs(oppositePoint[1] - point[1] - deltaY), minHeight, 1) / savedHeight;
    }
    const newWidth = AnnotationEditor._round(savedWidth * ratioX);
    const newHeight = AnnotationEditor._round(savedHeight * ratioY);
    transfOppositePoint = transf(...getOpposite(newWidth, newHeight));
    const newX = oppositeX - transfOppositePoint[0];
    const newY = oppositeY - transfOppositePoint[1];
    this.#initialRect ||= [this.x, this.y, this.width, this.height];
    this.width = newWidth;
    this.height = newHeight;
    this.x = newX;
    this.y = newY;
    this.setDims();
    this.fixAndSetPosition();
    this._onResizing();
  }
  _onResizing() {}
  altTextFinish() {
    this.#altText?.finish();
  }
  get toolbarButtons() {
    return null;
  }
  async addEditToolbar() {
    if (this._editToolbar || this.#isInEditMode) {
      return this._editToolbar;
    }
    this._editToolbar = new EditorToolbar(this);
    this.div.append(this._editToolbar.render());
    const {
      toolbarButtons
    } = this;
    if (toolbarButtons) {
      for (const [name, tool] of toolbarButtons) {
        await this._editToolbar.addButton(name, tool);
      }
    }
    if (!this.hasComment) {
      this._editToolbar.addButton("comment", this.addCommentButton());
    }
    this._editToolbar.addButton("delete");
    return this._editToolbar;
  }
  addCommentButtonInToolbar() {
    this._editToolbar?.addButtonBefore("comment", this.addCommentButton(), ".deleteButton");
  }
  removeCommentButtonFromToolbar() {
    this._editToolbar?.removeButton("comment");
  }
  removeEditToolbar() {
    this._editToolbar?.remove();
    this._editToolbar = null;
    this.#altText?.destroy();
  }
  addContainer(container) {
    const editToolbarDiv = this._editToolbar?.div;
    if (editToolbarDiv) {
      editToolbarDiv.before(container);
    } else {
      this.div.append(container);
    }
  }
  getClientDimensions() {
    return this.div.getBoundingClientRect();
  }
  createAltText() {
    if (!this.#altText) {
      AltText.initialize(AnnotationEditor._l10n);
      this.#altText = new AltText(this);
      if (this.#accessibilityData) {
        this.#altText.data = this.#accessibilityData;
        this.#accessibilityData = null;
      }
    }
    return this.#altText;
  }
  get altTextData() {
    return this.#altText?.data;
  }
  set altTextData(data) {
    if (!this.#altText) {
      return;
    }
    this.#altText.data = data;
  }
  get guessedAltText() {
    return this.#altText?.guessedText;
  }
  async setGuessedAltText(text) {
    await this.#altText?.setGuessedText(text);
  }
  serializeAltText(isForCopying) {
    return this.#altText?.serialize(isForCopying);
  }
  hasAltText() {
    return !!this.#altText && !this.#altText.isEmpty();
  }
  hasAltTextData() {
    return this.#altText?.hasData() ?? false;
  }
  focusCommentButton() {
    this.#comment?.focusButton();
  }
  addCommentButton() {
    return this.canAddComment ? this.#comment ||= new Comment(this) : null;
  }
  addStandaloneCommentButton() {
    if (!this._uiManager.hasCommentManager()) {
      return;
    }
    if (this.#commentStandaloneButton) {
      if (this._uiManager.isEditingMode()) {
        this.#commentStandaloneButton.classList.remove("hidden");
      }
      return;
    }
    if (!this.hasComment) {
      return;
    }
    this.#commentStandaloneButton = this.#comment.renderForStandalone();
    this.div.append(this.#commentStandaloneButton);
  }
  removeStandaloneCommentButton() {
    this.#comment.removeStandaloneCommentButton();
    this.#commentStandaloneButton = null;
  }
  hideStandaloneCommentButton() {
    this.#commentStandaloneButton?.classList.add("hidden");
  }
  get comment() {
    if (!this.#comment) {
      return null;
    }
    const {
      data: {
        richText,
        text,
        date,
        deleted
      }
    } = this.#comment;
    return {
      text,
      richText,
      date,
      deleted,
      color: this.getNonHCMColor(),
      opacity: this.opacity ?? 1
    };
  }
  set comment(value) {
    this.#comment ||= new Comment(this);
    if (typeof value === "object" && value !== null) {
      this.#comment.restoreData(value);
    } else {
      this.#comment.data = value;
    }
    if (this.hasComment) {
      this.removeCommentButtonFromToolbar();
      this.addStandaloneCommentButton();
      this._uiManager.updateComment(this);
    } else {
      this.addCommentButtonInToolbar();
      this.removeStandaloneCommentButton();
      this._uiManager.removeComment(this);
    }
  }
  setCommentData({
    comment,
    popupRef,
    richText
  }) {
    if (!popupRef) {
      return;
    }
    this.#comment ||= new Comment(this);
    this.#comment.setInitialText(comment, richText);
    if (!this.annotationElementId) {
      return;
    }
    const storedData = this._uiManager.getAndRemoveDataFromAnnotationStorage(this.annotationElementId);
    if (storedData) {
      this.updateFromAnnotationLayer(storedData);
    }
  }
  get hasEditedComment() {
    return this.#comment?.hasBeenEdited();
  }
  get hasDeletedComment() {
    return this.#comment?.isDeleted();
  }
  get hasComment() {
    return !!this.#comment && !this.#comment.isEmpty() && !this.#comment.isDeleted();
  }
  async editComment(options) {
    this.#comment ||= new Comment(this);
    this.#comment.edit(options);
  }
  toggleComment(isSelected, visibility = undefined) {
    if (this.hasComment) {
      this._uiManager.toggleComment(this, isSelected, visibility);
    }
  }
  setSelectedCommentButton(selected) {
    this.#comment.setSelectedButton(selected);
  }
  addComment(serialized) {
    if (this.hasEditedComment) {
      const DEFAULT_POPUP_WIDTH = 180;
      const DEFAULT_POPUP_HEIGHT = 100;
      const [,,, trY] = serialized.rect;
      const [pageWidth] = this.pageDimensions;
      const [pageX] = this.pageTranslation;
      const blX = pageX + pageWidth + 1;
      const blY = trY - DEFAULT_POPUP_HEIGHT;
      const trX = blX + DEFAULT_POPUP_WIDTH;
      serialized.popup = {
        contents: this.comment.text,
        deleted: this.comment.deleted,
        rect: [blX, blY, trX, trY]
      };
    }
  }
  updateFromAnnotationLayer({
    popup: {
      contents,
      deleted
    }
  }) {
    this.#comment.data = deleted ? null : contents;
  }
  get parentBoundingClientRect() {
    return this.parent.boundingClientRect;
  }
  render() {
    const div = this.div = document.createElement("div");
    div.setAttribute("data-editor-rotation", (360 - this.rotation) % 360);
    div.className = this.name;
    div.setAttribute("id", this.id);
    div.tabIndex = this.#disabled ? -1 : 0;
    div.setAttribute("role", "application");
    if (this.defaultL10nId) {
      div.setAttribute("data-l10n-id", this.defaultL10nId);
    }
    if (!this._isVisible) {
      div.classList.add("hidden");
    }
    this.setInForeground();
    this.#addFocusListeners();
    const [parentWidth, parentHeight] = this.parentDimensions;
    if (this.parentRotation % 180 !== 0) {
      div.style.maxWidth = `${(100 * parentHeight / parentWidth).toFixed(2)}%`;
      div.style.maxHeight = `${(100 * parentWidth / parentHeight).toFixed(2)}%`;
    }
    const [tx, ty] = this.getInitialTranslation();
    this.translate(tx, ty);
    bindEvents(this, div, ["keydown", "pointerdown", "dblclick"]);
    this.#addTouchManager();
    this.addStandaloneCommentButton();
    this._uiManager._editorUndoBar?.hide();
    return div;
  }
  #touchPinchStartCallback() {
    this.#savedDimensions = {
      savedX: this.x,
      savedY: this.y,
      savedWidth: this.width,
      savedHeight: this.height
    };
    this.#altText?.toggle(false);
    this.parent.togglePointerEvents(false);
  }
  #touchPinchCallback(_origin, prevDistance, distance) {
    const slowDownFactor = 0.7;
    let factor = slowDownFactor * (distance / prevDistance) + 1 - slowDownFactor;
    if (factor === 1) {
      return;
    }
    const rotationMatrix = this.#getRotationMatrix(this.rotation);
    const transf = (x, y) => [rotationMatrix[0] * x + rotationMatrix[2] * y, rotationMatrix[1] * x + rotationMatrix[3] * y];
    const [parentWidth, parentHeight] = this.parentDimensions;
    const savedX = this.x;
    const savedY = this.y;
    const savedWidth = this.width;
    const savedHeight = this.height;
    const minWidth = AnnotationEditor.MIN_SIZE / parentWidth;
    const minHeight = AnnotationEditor.MIN_SIZE / parentHeight;
    factor = Math.max(Math.min(factor, 1 / savedWidth, 1 / savedHeight), minWidth / savedWidth, minHeight / savedHeight);
    const newWidth = AnnotationEditor._round(savedWidth * factor);
    const newHeight = AnnotationEditor._round(savedHeight * factor);
    if (newWidth === savedWidth && newHeight === savedHeight) {
      return;
    }
    this.#initialRect ||= [savedX, savedY, savedWidth, savedHeight];
    const transfCenterPoint = transf(savedWidth / 2, savedHeight / 2);
    const centerX = AnnotationEditor._round(savedX + transfCenterPoint[0]);
    const centerY = AnnotationEditor._round(savedY + transfCenterPoint[1]);
    const newTransfCenterPoint = transf(newWidth / 2, newHeight / 2);
    this.x = centerX - newTransfCenterPoint[0];
    this.y = centerY - newTransfCenterPoint[1];
    this.width = newWidth;
    this.height = newHeight;
    this.setDims();
    this.fixAndSetPosition();
    this._onResizing();
  }
  #touchPinchEndCallback() {
    this.#altText?.toggle(true);
    this.parent.togglePointerEvents(true);
    this.#addResizeToUndoStack();
  }
  pointerdown(event) {
    const {
      isMac
    } = FeatureTest.platform;
    if (event.button !== 0 || event.ctrlKey && isMac) {
      event.preventDefault();
      return;
    }
    this.#hasBeenClicked = true;
    if (this._isDraggable) {
      this.#setUpDragSession(event);
      return;
    }
    this.#selectOnPointerEvent(event);
  }
  #selectOnPointerEvent(event) {
    const {
      isMac
    } = FeatureTest.platform;
    if (event.ctrlKey && !isMac || event.shiftKey || event.metaKey && isMac) {
      this.parent.toggleSelected(this);
    } else {
      this.parent.setSelected(this);
    }
  }
  #setUpDragSession(event) {
    const {
      isSelected
    } = this;
    this._uiManager.setUpDragSession();
    let hasDraggingStarted = false;
    const ac = new AbortController();
    const signal = this._uiManager.combinedSignal(ac);
    const opts = {
      capture: true,
      passive: false,
      signal
    };
    const cancelDrag = e => {
      ac.abort();
      this.#dragPointerId = null;
      this.#hasBeenClicked = false;
      if (!this._uiManager.endDragSession()) {
        this.#selectOnPointerEvent(e);
      }
      if (hasDraggingStarted) {
        this._onStopDragging();
      }
    };
    if (isSelected) {
      this.#prevDragX = event.clientX;
      this.#prevDragY = event.clientY;
      this.#dragPointerId = event.pointerId;
      this.#dragPointerType = event.pointerType;
      window.addEventListener("pointermove", e => {
        if (!hasDraggingStarted) {
          hasDraggingStarted = true;
          this._uiManager.toggleComment(this, true, false);
          this._onStartDragging();
        }
        const {
          clientX: x,
          clientY: y,
          pointerId
        } = e;
        if (pointerId !== this.#dragPointerId) {
          stopEvent(e);
          return;
        }
        const [tx, ty] = this.screenToPageTranslation(x - this.#prevDragX, y - this.#prevDragY);
        this.#prevDragX = x;
        this.#prevDragY = y;
        this._uiManager.dragSelectedEditors(tx, ty);
        this.div.scrollIntoView({
          block: "nearest"
        });
      }, opts);
      window.addEventListener("touchmove", stopEvent, opts);
      window.addEventListener("pointerdown", e => {
        if (e.pointerType === this.#dragPointerType) {
          if (this.#touchManager || e.isPrimary) {
            cancelDrag(e);
          }
        }
        stopEvent(e);
      }, opts);
    }
    const pointerUpCallback = e => {
      if (!this.#dragPointerId || this.#dragPointerId === e.pointerId) {
        cancelDrag(e);
        return;
      }
      stopEvent(e);
    };
    window.addEventListener("pointerup", pointerUpCallback, {
      signal
    });
    window.addEventListener("blur", pointerUpCallback, {
      signal
    });
  }
  _onStartDragging() {}
  _onStopDragging() {}
  moveInDOM() {
    if (this.#moveInDOMTimeout) {
      clearTimeout(this.#moveInDOMTimeout);
    }
    this.#moveInDOMTimeout = setTimeout(() => {
      this.#moveInDOMTimeout = null;
      this.parent?.moveEditorInDOM(this);
    }, 0);
  }
  _setParentAndPosition(parent, x, y) {
    parent.changeParent(this);
    this.x = x;
    this.y = y;
    this.fixAndSetPosition();
    this._onTranslated();
  }
  getRect(tx, ty, rotation = this.rotation) {
    const scale = this.parentScale;
    const [pageWidth, pageHeight] = this.pageDimensions;
    const [pageX, pageY] = this.pageTranslation;
    const shiftX = tx / scale;
    const shiftY = ty / scale;
    const x = this.x * pageWidth;
    const y = this.y * pageHeight;
    const width = this.width * pageWidth;
    const height = this.height * pageHeight;
    switch (rotation) {
      case 0:
        return [x + shiftX + pageX, pageHeight - y - shiftY - height + pageY, x + shiftX + width + pageX, pageHeight - y - shiftY + pageY];
      case 90:
        return [x + shiftY + pageX, pageHeight - y + shiftX + pageY, x + shiftY + height + pageX, pageHeight - y + shiftX + width + pageY];
      case 180:
        return [x - shiftX - width + pageX, pageHeight - y + shiftY + pageY, x - shiftX + pageX, pageHeight - y + shiftY + height + pageY];
      case 270:
        return [x - shiftY - height + pageX, pageHeight - y - shiftX - width + pageY, x - shiftY + pageX, pageHeight - y - shiftX + pageY];
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
  getPDFRect() {
    return this.getRect(0, 0);
  }
  getNonHCMColor() {
    return this.color && AnnotationEditor._colorManager.convert(this._uiManager.getNonHCMColor(this.color));
  }
  onUpdatedColor() {
    this.#comment?.onUpdatedColor();
  }
  getData() {
    const {
      comment: {
        text: str,
        color,
        date,
        opacity,
        deleted,
        richText
      },
      uid: id,
      pageIndex,
      creationDate,
      modificationDate
    } = this;
    return {
      id,
      pageIndex,
      rect: this.getPDFRect(),
      richText,
      contentsObj: {
        str
      },
      creationDate,
      modificationDate: date || modificationDate,
      popupRef: !deleted,
      color,
      opacity
    };
  }
  onceAdded(focus) {}
  isEmpty() {
    return false;
  }
  enableEditMode() {
    if (this.isInEditMode()) {
      return false;
    }
    this.parent.setEditingState(false);
    this.#isInEditMode = true;
    return true;
  }
  disableEditMode() {
    if (!this.isInEditMode()) {
      return false;
    }
    this.parent.setEditingState(true);
    this.#isInEditMode = false;
    return true;
  }
  isInEditMode() {
    return this.#isInEditMode;
  }
  shouldGetKeyboardEvents() {
    return this.#isResizerEnabledForKeyboard;
  }
  needsToBeRebuilt() {
    return this.div && !this.isAttachedToDOM;
  }
  get isOnScreen() {
    const {
      top,
      left,
      bottom,
      right
    } = this.getClientDimensions();
    const {
      innerHeight,
      innerWidth
    } = window;
    return left < innerWidth && right > 0 && top < innerHeight && bottom > 0;
  }
  #addFocusListeners() {
    if (this.#focusAC || !this.div) {
      return;
    }
    this.#focusAC = new AbortController();
    const signal = this._uiManager.combinedSignal(this.#focusAC);
    this.div.addEventListener("focusin", this.focusin.bind(this), {
      signal
    });
    this.div.addEventListener("focusout", this.focusout.bind(this), {
      signal
    });
  }
  #addTouchManager() {
    if (this.#touchManager || !this.div || !this.isResizable || !this._uiManager._supportsPinchToZoom) {
      return;
    }
    this.#touchManager = new TouchManager({
      container: this.div,
      isPinchingDisabled: () => !this.isSelected,
      onPinchStart: this.#touchPinchStartCallback.bind(this),
      onPinching: this.#touchPinchCallback.bind(this),
      onPinchEnd: this.#touchPinchEndCallback.bind(this),
      signal: this._uiManager._signal
    });
  }
  rebuild() {
    this.#addFocusListeners();
    this.#addTouchManager();
  }
  rotate(_angle) {}
  resize() {}
  serializeDeleted() {
    return {
      id: this.annotationElementId,
      deleted: true,
      pageIndex: this.pageIndex,
      popupRef: this._initialData?.popupRef || ""
    };
  }
  serialize(isForCopying = false, context = null) {
    return {
      annotationType: this.mode,
      pageIndex: this.pageIndex,
      rect: this.getPDFRect(),
      rotation: this.rotation,
      structTreeParentId: this._structTreeParentId,
      popupRef: this._initialData?.popupRef || ""
    };
  }
  static async deserialize(data, parent, uiManager) {
    const editor = new this.prototype.constructor({
      parent,
      id: uiManager.getId(),
      uiManager,
      annotationElementId: data.annotationElementId,
      creationDate: data.creationDate,
      modificationDate: data.modificationDate
    });
    editor.rotation = data.rotation;
    editor.#accessibilityData = data.accessibilityData;
    editor._isCopy = data.isCopy || false;
    const [pageWidth, pageHeight] = editor.pageDimensions;
    const [x, y, width, height] = editor.getRectInCurrentCoords(data.rect, pageHeight);
    editor.x = x / pageWidth;
    editor.y = y / pageHeight;
    editor.width = width / pageWidth;
    editor.height = height / pageHeight;
    return editor;
  }
  get hasBeenModified() {
    return !!this.annotationElementId && (this.deleted || this.serialize() !== null);
  }
  remove() {
    this.#focusAC?.abort();
    this.#focusAC = null;
    if (!this.isEmpty()) {
      this.commit();
    }
    this.#touchManager?.destroy();
    this.#touchManager = null;
    if (this.parent) {
      this.parent.remove(this);
    } else {
      this._uiManager.removeEditor(this);
    }
    this.hideCommentPopup();
    if (this.#moveInDOMTimeout) {
      clearTimeout(this.#moveInDOMTimeout);
      this.#moveInDOMTimeout = null;
    }
    this.#stopResizing();
    this.removeEditToolbar();
    if (this.#telemetryTimeouts) {
      for (const timeout of this.#telemetryTimeouts.values()) {
        clearTimeout(timeout);
      }
      this.#telemetryTimeouts = null;
    }
    this.parent = null;
    this.#fakeAnnotation?.remove();
    this.#fakeAnnotation = null;
  }
  get isResizable() {
    return false;
  }
  makeResizable() {
    if (this.isResizable) {
      this.#createResizers();
      this.#resizersDiv.classList.remove("hidden");
    }
  }
  get toolbarPosition() {
    return null;
  }
  get commentButtonPosition() {
    return this._uiManager.direction === "ltr" ? [1, 0] : [0, 0];
  }
  get commentButtonPositionInPage() {
    const {
      commentButtonPosition: [posX, posY]
    } = this;
    const [blX, blY, trX, trY] = this.getPDFRect();
    return [AnnotationEditor._round(blX + (trX - blX) * posX), AnnotationEditor._round(blY + (trY - blY) * (1 - posY))];
  }
  get commentButtonColor() {
    return this._uiManager.makeCommentColor(this.getNonHCMColor(), this.opacity);
  }
  get commentPopupPosition() {
    return this.#comment.commentPopupPositionInLayer;
  }
  set commentPopupPosition(pos) {
    this.#comment.commentPopupPositionInLayer = pos;
  }
  hasDefaultPopupPosition() {
    return this.#comment.hasDefaultPopupPosition();
  }
  get commentButtonWidth() {
    return this.#comment.commentButtonWidth;
  }
  get elementBeforePopup() {
    return this.div;
  }
  setCommentButtonStates(options) {
    this.#comment?.setCommentButtonStates(options);
  }
  keydown(event) {
    if (!this.isResizable || event.target !== this.div || event.key !== "Enter") {
      return;
    }
    this._uiManager.setSelected(this);
    this.#savedDimensions = {
      savedX: this.x,
      savedY: this.y,
      savedWidth: this.width,
      savedHeight: this.height
    };
    const children = this.#resizersDiv.children;
    if (!this.#allResizerDivs) {
      this.#allResizerDivs = Array.from(children);
      const boundResizerKeydown = this.#resizerKeydown.bind(this);
      const boundResizerBlur = this.#resizerBlur.bind(this);
      const signal = this._uiManager._signal;
      for (const div of this.#allResizerDivs) {
        const name = div.getAttribute("data-resizer-name");
        div.setAttribute("role", "spinbutton");
        div.addEventListener("keydown", boundResizerKeydown, {
          signal
        });
        div.addEventListener("blur", boundResizerBlur, {
          signal
        });
        div.addEventListener("focus", this.#resizerFocus.bind(this, name), {
          signal
        });
        div.setAttribute("data-l10n-id", AnnotationEditor._l10nResizer[name]);
      }
    }
    const first = this.#allResizerDivs[0];
    let firstPosition = 0;
    for (const div of children) {
      if (div === first) {
        break;
      }
      firstPosition++;
    }
    const nextFirstPosition = (360 - this.rotation + this.parentRotation) % 360 / 90 * (this.#allResizerDivs.length / 4);
    if (nextFirstPosition !== firstPosition) {
      if (nextFirstPosition < firstPosition) {
        for (let i = 0; i < firstPosition - nextFirstPosition; i++) {
          this.#resizersDiv.append(this.#resizersDiv.firstElementChild);
        }
      } else if (nextFirstPosition > firstPosition) {
        for (let i = 0; i < nextFirstPosition - firstPosition; i++) {
          this.#resizersDiv.firstElementChild.before(this.#resizersDiv.lastElementChild);
        }
      }
      let i = 0;
      for (const child of children) {
        const div = this.#allResizerDivs[i++];
        const name = div.getAttribute("data-resizer-name");
        child.setAttribute("data-l10n-id", AnnotationEditor._l10nResizer[name]);
      }
    }
    this.#setResizerTabIndex(0);
    this.#isResizerEnabledForKeyboard = true;
    this.#resizersDiv.firstElementChild.focus({
      focusVisible: true
    });
    event.preventDefault();
    event.stopImmediatePropagation();
  }
  #resizerKeydown(event) {
    AnnotationEditor._resizerKeyboardManager.exec(this, event);
  }
  #resizerBlur(event) {
    if (this.#isResizerEnabledForKeyboard && event.relatedTarget?.parentNode !== this.#resizersDiv) {
      this.#stopResizing();
    }
  }
  #resizerFocus(name) {
    this.#focusedResizerName = this.#isResizerEnabledForKeyboard ? name : "";
  }
  #setResizerTabIndex(value) {
    if (!this.#allResizerDivs) {
      return;
    }
    for (const div of this.#allResizerDivs) {
      div.tabIndex = value;
    }
  }
  _resizeWithKeyboard(x, y) {
    if (!this.#isResizerEnabledForKeyboard) {
      return;
    }
    this.#resizerPointermove(this.#focusedResizerName, {
      deltaX: x,
      deltaY: y,
      fromKeyboard: true
    });
  }
  #stopResizing() {
    this.#isResizerEnabledForKeyboard = false;
    this.#setResizerTabIndex(-1);
    this.#addResizeToUndoStack();
  }
  _stopResizingWithKeyboard() {
    this.#stopResizing();
    this.div.focus();
  }
  select() {
    if (this.isSelected && this._editToolbar) {
      this._editToolbar.show();
      return;
    }
    this.isSelected = true;
    this.makeResizable();
    this.div?.classList.add("selectedEditor");
    if (!this._editToolbar) {
      this.addEditToolbar().then(() => {
        if (this.div?.classList.contains("selectedEditor")) {
          this.#showEditToolbar();
        }
      });
      return;
    }
    this.#showEditToolbar();
    this.#altText?.toggleAltTextBadge(false);
  }
  #showEditToolbar() {
    this._editToolbar?.show();
    if (this._uiManager._keepToolbarInPage) {
      this.fixAndSetPosition();
      this._onTranslated();
    }
  }
  focus() {
    if (this.div && !this.div.contains(document.activeElement)) {
      setTimeout(() => this.div?.focus({
        preventScroll: true
      }), 0);
    }
  }
  unselect() {
    if (!this.isSelected) {
      return;
    }
    this.isSelected = false;
    this.#resizersDiv?.classList.add("hidden");
    this.div?.classList.remove("selectedEditor");
    if (this.div?.contains(document.activeElement)) {
      this._uiManager.currentLayer.div.focus({
        preventScroll: true
      });
    }
    this._editToolbar?.hide();
    this.#altText?.toggleAltTextBadge(true);
    this.hideCommentPopup();
  }
  hideCommentPopup() {
    if (this.hasComment) {
      this._uiManager.toggleComment(null);
    }
  }
  updateParams(type, value) {}
  disableEditing() {}
  enableEditing() {}
  get canChangeContent() {
    return false;
  }
  enterInEditMode() {
    if (!this.canChangeContent) {
      return;
    }
    this.enableEditMode();
    this.div.focus();
  }
  dblclick(event) {
    if (event.target.nodeName === "BUTTON") {
      return;
    }
    this.enterInEditMode();
    this.parent.updateToolbar({
      mode: this.constructor._editorType,
      editId: this.uid
    });
  }
  getElementForAltText() {
    return this.div;
  }
  get contentDiv() {
    return this.div;
  }
  get isEditing() {
    return this.#isEditing;
  }
  set isEditing(value) {
    this.#isEditing = value;
    if (!this.parent) {
      return;
    }
    if (value) {
      this.parent.setSelected(this);
      this.parent.setActiveEditor(this);
    } else {
      this.parent.setActiveEditor(null);
    }
  }
  static get MIN_SIZE() {
    return 16;
  }
  static canCreateNewEmptyEditor() {
    return true;
  }
  get telemetryInitialData() {
    return {
      action: "added"
    };
  }
  get telemetryFinalData() {
    return null;
  }
  _reportTelemetry(data, mustWait = false) {
    if (mustWait) {
      this.#telemetryTimeouts ||= new Map();
      const {
        action
      } = data;
      let timeout = this.#telemetryTimeouts.get(action);
      if (timeout) {
        clearTimeout(timeout);
      }
      timeout = setTimeout(() => {
        this._reportTelemetry(data);
        this.#telemetryTimeouts.delete(action);
        if (this.#telemetryTimeouts.size === 0) {
          this.#telemetryTimeouts = null;
        }
      }, AnnotationEditor._telemetryTimeout);
      this.#telemetryTimeouts.set(action, timeout);
      return;
    }
    data.type ||= this.editorType;
    this._uiManager._eventBus.dispatch("reporttelemetry", {
      source: this,
      details: {
        type: "editing",
        data
      }
    });
  }
  show(visible = this._isVisible) {
    this.div.classList.toggle("hidden", !visible);
    this._isVisible = visible;
  }
  enable() {
    if (this.div) {
      this.div.tabIndex = 0;
    }
    this.#disabled = false;
  }
  disable() {
    if (this.div) {
      this.div.tabIndex = -1;
    }
    this.#disabled = true;
  }
  updateFakeAnnotationElement(annotationLayer) {
    if (!this.#fakeAnnotation && !this.deleted) {
      this.#fakeAnnotation = annotationLayer.addFakeAnnotation(this);
      return;
    }
    if (this.deleted) {
      this.#fakeAnnotation.remove();
      this.#fakeAnnotation = null;
      return;
    }
    if (this.hasEditedComment || this._hasBeenMoved || this._hasBeenResized) {
      this.#fakeAnnotation.updateEdited({
        rect: this.getPDFRect(),
        popup: this.comment
      });
    }
  }
  renderAnnotationElement(annotation) {
    if (this.deleted) {
      annotation.hide();
      return null;
    }
    let content = annotation.container.querySelector(".annotationContent");
    if (!content) {
      content = document.createElement("div");
      content.classList.add("annotationContent", this.editorType);
      annotation.container.prepend(content);
    } else if (content.nodeName === "CANVAS") {
      const canvas = content;
      content = document.createElement("div");
      content.classList.add("annotationContent", this.editorType);
      canvas.before(content);
    }
    return content;
  }
  resetAnnotationElement(annotation) {
    const {
      firstElementChild
    } = annotation.container;
    if (firstElementChild?.nodeName === "DIV" && firstElementChild.classList.contains("annotationContent")) {
      firstElementChild.remove();
    }
  }
}
class FakeEditor extends AnnotationEditor {
  constructor(params) {
    super(params);
    this.annotationElementId = params.annotationElementId;
    this.deleted = true;
  }
  serialize() {
    return this.serializeDeleted();
  }
}

;// ./src/shared/murmurhash3.js
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
    } else if (ArrayBuffer.isView(input)) {
      data = input.slice();
      length = data.byteLength;
    } else {
      throw new Error("Invalid data format, must be a string or TypedArray.");
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
    return (h1 >>> 0).toString(16).padStart(8, "0") + (h2 >>> 0).toString(16).padStart(8, "0");
  }
}

;// ./src/display/annotation_storage.js



const SerializableEmpty = Object.freeze({
  map: null,
  hash: "",
  transfer: undefined
});
class AnnotationStorage {
  #modified = false;
  #modifiedIds = null;
  #editorsMap = null;
  #storage = new Map();
  onSetModified = null;
  onResetModified = null;
  onAnnotationEditor = null;
  getValue(key, defaultValue) {
    const value = this.#storage.get(key);
    return value === undefined ? defaultValue : Object.assign(defaultValue, value);
  }
  getRawValue(key) {
    return this.#storage.get(key);
  }
  remove(key) {
    const storedValue = this.#storage.get(key);
    if (storedValue === undefined) {
      return;
    }
    if (storedValue instanceof AnnotationEditor) {
      this.#editorsMap.delete(storedValue.annotationElementId);
    }
    this.#storage.delete(key);
    if (this.#storage.size === 0) {
      this.resetModified();
    }
    if (this.#storage.values().some(v => v instanceof AnnotationEditor)) {
      return;
    }
    this.onAnnotationEditor?.(null);
  }
  setValue(key, value) {
    const obj = this.#storage.get(key);
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
      this.#storage.set(key, value);
    }
    if (modified) {
      this.#setModified();
    }
    if (value instanceof AnnotationEditor) {
      (this.#editorsMap ||= new Map()).set(value.annotationElementId, value);
      this.onAnnotationEditor?.(value.constructor._type);
    }
  }
  has(key) {
    return this.#storage.has(key);
  }
  get size() {
    return this.#storage.size;
  }
  #setModified() {
    if (!this.#modified) {
      this.#modified = true;
      this.onSetModified?.();
    }
  }
  resetModified() {
    if (this.#modified) {
      this.#modified = false;
      this.onResetModified?.();
    }
  }
  get print() {
    return new PrintAnnotationStorage(this);
  }
  get serializable() {
    if (this.#storage.size === 0) {
      return SerializableEmpty;
    }
    const map = new Map(),
      hash = new MurmurHash3_64(),
      transfer = [];
    const context = Object.create(null);
    let hasBitmap = false;
    for (const [key, val] of this.#storage) {
      const serialized = val instanceof AnnotationEditor ? val.serialize(false, context) : val;
      if (val.page) {
        val.pageIndex = val.page._pageIndex;
        delete val.page;
      }
      if (serialized) {
        map.set(key, serialized);
        hash.update(`${key}:${JSON.stringify(serialized)}`);
        hasBitmap ||= !!serialized.bitmap;
      }
    }
    if (hasBitmap) {
      for (const value of map.values()) {
        if (value.bitmap) {
          transfer.push(value.bitmap);
        }
      }
    }
    return map.size > 0 ? {
      map,
      hash: hash.hexdigest(),
      transfer
    } : SerializableEmpty;
  }
  get editorStats() {
    let stats = null;
    const typeToEditor = new Map();
    let numberOfEditedComments = 0;
    let numberOfDeletedComments = 0;
    for (const value of this.#storage.values()) {
      if (!(value instanceof AnnotationEditor)) {
        if (value.popup) {
          if (value.popup.deleted) {
            numberOfDeletedComments += 1;
          } else {
            numberOfEditedComments += 1;
          }
        }
        continue;
      }
      if (value.isCommentDeleted) {
        numberOfDeletedComments += 1;
      } else if (value.hasEditedComment) {
        numberOfEditedComments += 1;
      }
      const editorStats = value.telemetryFinalData;
      if (!editorStats) {
        continue;
      }
      const {
        type
      } = editorStats;
      typeToEditor.getOrInsertComputed(type, () => Object.getPrototypeOf(value).constructor);
      stats ||= Object.create(null);
      const map = stats[type] ||= new Map();
      for (const [key, val] of Object.entries(editorStats)) {
        if (key === "type") {
          continue;
        }
        const counters = map.getOrInsertComputed(key, makeMap);
        counters.set(val, (counters.get(val) ?? 0) + 1);
      }
    }
    if (numberOfDeletedComments > 0 || numberOfEditedComments > 0) {
      stats ||= Object.create(null);
      stats.comments = {
        deleted: numberOfDeletedComments,
        edited: numberOfEditedComments
      };
    }
    if (!stats) {
      return null;
    }
    for (const [type, editor] of typeToEditor) {
      stats[type] = editor.computeTelemetryFinalData(stats[type]);
    }
    return stats;
  }
  resetModifiedIds() {
    this.#modifiedIds = null;
  }
  updateEditor(annotationId, data) {
    const value = this.#editorsMap?.get(annotationId);
    if (value) {
      value.updateFromAnnotationLayer(data);
      return true;
    }
    return false;
  }
  getEditor(annotationId) {
    return this.#editorsMap?.get(annotationId) || null;
  }
  get modifiedIds() {
    if (this.#modifiedIds) {
      return this.#modifiedIds;
    }
    const ids = [];
    if (this.#editorsMap) {
      for (const value of this.#editorsMap.values()) {
        if (!value.serialize()) {
          continue;
        }
        ids.push(value.annotationElementId);
      }
    }
    let hash = "";
    if (ids.length) {
      const h = new MurmurHash3_64();
      h.update(ids.join(","));
      hash = h.hexdigest();
    }
    return this.#modifiedIds = {
      ids: new Set(ids),
      hash
    };
  }
  [Symbol.iterator]() {
    return this.#storage.entries();
  }
}
class PrintAnnotationStorage extends AnnotationStorage {
  #serializable = SerializableEmpty;
  constructor(parent) {
    super();
    const {
      serializable
    } = parent;
    if (serializable === SerializableEmpty) {
      return;
    }
    const {
      map,
      hash,
      transfer
    } = serializable;
    const clone = structuredClone(map, transfer ? {
      transfer
    } : null);
    this.#serializable = {
      map: clone,
      hash,
      transfer: []
    };
  }
  get print() {
    unreachable("Should not call PrintAnnotationStorage.print");
  }
  get serializable() {
    return this.#serializable;
  }
  get modifiedIds() {
    return shadow(this, "modifiedIds", {
      ids: new Set(),
      hash: ""
    });
  }
}

;// ./src/display/api_utils.js

function deprecated(details) {
  console.log("Deprecated API usage: " + details);
}
function getUrlProp(val) {
  if (val instanceof URL) {
    return val;
  }
  if (typeof val === "string") {
    if (isNodeJS) {
      if (/^[a-z][a-z0-9\-+.]+:/i.test(val)) {
        return new URL(val);
      }
      const url = process.getBuiltinModule("url");
      return new URL(url.pathToFileURL(val));
    }
    const url = URL.parse(val, window.location);
    if (url) {
      return url;
    }
  }
  throw new Error("Invalid PDF url data: " + "either string or URL-object is expected in the url property.");
}
function getDataProp(val) {
  if (isNodeJS && typeof Buffer !== "undefined" && val instanceof Buffer) {
    throw new Error("Please provide binary data as `Uint8Array`, rather than `Buffer`.");
  }
  if (val instanceof Uint8Array && val.byteLength === val.buffer.byteLength) {
    return val;
  }
  if (typeof val === "string") {
    return stringToBytes(val);
  }
  if (val instanceof ArrayBuffer || ArrayBuffer.isView(val) || typeof val === "object" && !isNaN(val?.length)) {
    return new Uint8Array(val);
  }
  throw new Error("Invalid PDF binary data: either TypedArray, " + "string, or array-like object is expected in the data property.");
}
function getFactoryUrlProp(val) {
  if (typeof val !== "string") {
    return null;
  }
  if (val.endsWith("/")) {
    return val;
  }
  throw new Error(`Invalid factory url: "${val}" must include trailing slash.`);
}
const isRefProxy = v => typeof v === "object" && Number.isInteger(v?.num) && v.num >= 0 && Number.isInteger(v?.gen) && v.gen >= 0;
const isNameProxy = v => typeof v === "object" && typeof v?.name === "string";
const isValidExplicitDest = _isValidExplicitDest.bind(null, isRefProxy, isNameProxy);
function isSameOrigin(baseUrl, otherUrl) {
  const base = URL.parse(baseUrl);
  if (!base?.origin || base.origin === "null") {
    return false;
  }
  const other = new URL(otherUrl, base);
  return base.origin === other.origin;
}
function getWorkerSrc(src) {
  if (!isSameOrigin(window.location, src)) {
    const wrapper = `await import("${new URL(src, window.location).href}");`;
    return URL.createObjectURL(new Blob([wrapper], {
      type: "text/javascript"
    }));
  }
  return src;
}
class LoopbackPort {
  #listeners = new Map();
  #deferred = Promise.resolve();
  postMessage(obj, transfer) {
    const event = {
      data: structuredClone(obj, transfer ? {
        transfer
      } : null)
    };
    this.#deferred.then(() => {
      for (const [listener] of this.#listeners) {
        listener.call(this, event);
      }
    });
  }
  addEventListener(name, listener, options = null) {
    let rmAbort = null;
    if (options?.signal instanceof AbortSignal) {
      const {
        signal
      } = options;
      if (signal.aborted) {
        warn("LoopbackPort - cannot use an `aborted` signal.");
        return;
      }
      const onAbort = () => this.removeEventListener(name, listener);
      rmAbort = () => signal.removeEventListener("abort", onAbort);
      signal.addEventListener("abort", onAbort);
    }
    this.#listeners.set(listener, rmAbort);
  }
  removeEventListener(name, listener) {
    const rmAbort = this.#listeners.get(listener);
    rmAbort?.();
    this.#listeners.delete(listener);
  }
  terminate() {
    for (const [, rmAbort] of this.#listeners) {
      rmAbort?.();
    }
    this.#listeners.clear();
  }
}
class StatTimer {
  #started = new Map();
  times = [];
  time(name) {
    if (this.#started.has(name)) {
      warn(`Timer is already running for ${name}`);
    }
    this.#started.set(name, Date.now());
  }
  timeEnd(name) {
    if (!this.#started.has(name)) {
      warn(`Timer has not been started for ${name}`);
    }
    this.times.push({
      name,
      start: this.#started.get(name),
      end: Date.now()
    });
    this.#started.delete(name);
  }
  toString() {
    const longest = Math.max(...this.times.map(t => t.name.length));
    return this.times.map(t => `${t.name.padEnd(longest)} ${t.end - t.start}ms\n`).join("");
  }
}

;// ./src/display/webgpu.js
const MESH_WGSL = `
struct Uniforms {
  offsetX      : f32,
  offsetY      : f32,
  scaleX       : f32,
  scaleY       : f32,
  paddedWidth  : f32,
  paddedHeight : f32,
  borderSize   : f32,
  _pad         : f32,
};

@group(0) @binding(0) var<uniform> u : Uniforms;

struct VertexInput {
  @location(0) position : vec2<f32>,
  @location(1) color    : vec4<f32>,
};

struct VertexOutput {
  @builtin(position) position : vec4<f32>,
  @location(0)       color    : vec3<f32>,
};

@vertex
fn vs_main(in : VertexInput) -> VertexOutput {
  var out : VertexOutput;
  let cx = (in.position.x + u.offsetX) * u.scaleX;
  let cy = (in.position.y + u.offsetY) * u.scaleY;
  out.position = vec4<f32>(
    ((cx + u.borderSize) / u.paddedWidth) * 2.0 - 1.0,
    1.0 - ((cy + u.borderSize) / u.paddedHeight) * 2.0,
    0.0,
    1.0
  );
  out.color = in.color.rgb;
  return out;
}

@fragment
fn fs_main(in : VertexOutput) -> @location(0) vec4<f32> {
  return vec4<f32>(in.color, 1.0);
}
`;
class WebGPU {
  #initPromise = null;
  #device = null;
  #meshPipeline = null;
  #preferredFormat = null;
  async #initGPU() {
    if (!globalThis.navigator?.gpu) {
      return false;
    }
    try {
      const adapter = await navigator.gpu.requestAdapter();
      if (!adapter) {
        return false;
      }
      this.#preferredFormat = navigator.gpu.getPreferredCanvasFormat();
      this.#device = await adapter.requestDevice();
      return true;
    } catch {
      return false;
    }
  }
  init() {
    return this.#initPromise ||= this.#initGPU();
  }
  get isReady() {
    return this.#device !== null;
  }
  loadMeshShader() {
    if (!this.#device || this.#meshPipeline) {
      return;
    }
    const shaderModule = this.#device.createShaderModule({
      code: MESH_WGSL
    });
    this.#meshPipeline = this.#device.createRenderPipeline({
      layout: "auto",
      vertex: {
        module: shaderModule,
        entryPoint: "vs_main",
        buffers: [{
          arrayStride: 2 * 4,
          attributes: [{
            shaderLocation: 0,
            offset: 0,
            format: "float32x2"
          }]
        }, {
          arrayStride: 4,
          attributes: [{
            shaderLocation: 1,
            offset: 0,
            format: "unorm8x4"
          }]
        }]
      },
      fragment: {
        module: shaderModule,
        entryPoint: "fs_main",
        targets: [{
          format: this.#preferredFormat
        }]
      },
      primitive: {
        topology: "triangle-list"
      }
    });
  }
  draw(posData, colData, vertexCount, context, backgroundColor, paddedWidth, paddedHeight, borderSize) {
    this.loadMeshShader();
    const device = this.#device;
    const {
      offsetX,
      offsetY,
      scaleX,
      scaleY
    } = context;
    const posBuffer = device.createBuffer({
      size: Math.max(posData.byteLength, 4),
      usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST
    });
    if (posData.byteLength > 0) {
      device.queue.writeBuffer(posBuffer, 0, posData);
    }
    const colBuffer = device.createBuffer({
      size: Math.max(colData.byteLength, 4),
      usage: GPUBufferUsage.VERTEX | GPUBufferUsage.COPY_DST
    });
    if (colData.byteLength > 0) {
      device.queue.writeBuffer(colBuffer, 0, colData);
    }
    const uniformBuffer = device.createBuffer({
      size: 8 * 4,
      usage: GPUBufferUsage.UNIFORM | GPUBufferUsage.COPY_DST
    });
    device.queue.writeBuffer(uniformBuffer, 0, new Float32Array([offsetX, offsetY, scaleX, scaleY, paddedWidth, paddedHeight, borderSize, 0]));
    const bindGroup = device.createBindGroup({
      layout: this.#meshPipeline.getBindGroupLayout(0),
      entries: [{
        binding: 0,
        resource: {
          buffer: uniformBuffer
        }
      }]
    });
    const offscreen = new OffscreenCanvas(paddedWidth, paddedHeight);
    const gpuCtx = offscreen.getContext("webgpu");
    gpuCtx.configure({
      device,
      format: this.#preferredFormat,
      alphaMode: backgroundColor ? "opaque" : "premultiplied"
    });
    const clearValue = backgroundColor ? {
      r: backgroundColor[0] / 255,
      g: backgroundColor[1] / 255,
      b: backgroundColor[2] / 255,
      a: 1
    } : {
      r: 0,
      g: 0,
      b: 0,
      a: 0
    };
    const commandEncoder = device.createCommandEncoder();
    const renderPass = commandEncoder.beginRenderPass({
      colorAttachments: [{
        view: gpuCtx.getCurrentTexture().createView(),
        clearValue,
        loadOp: "clear",
        storeOp: "store"
      }]
    });
    if (vertexCount > 0) {
      renderPass.setPipeline(this.#meshPipeline);
      renderPass.setBindGroup(0, bindGroup);
      renderPass.setVertexBuffer(0, posBuffer);
      renderPass.setVertexBuffer(1, colBuffer);
      renderPass.draw(vertexCount);
    }
    renderPass.end();
    device.queue.submit([commandEncoder.finish()]);
    posBuffer.destroy();
    colBuffer.destroy();
    uniformBuffer.destroy();
    return offscreen.transferToImageBitmap();
  }
}
const _webGPU = new WebGPU();
function initGPU() {
  return _webGPU.init();
}
function isGPUReady() {
  return _webGPU.isReady;
}
function loadMeshShader() {
  _webGPU.loadMeshShader();
}
function drawMeshWithGPU(posData, colData, vertexCount, context, backgroundColor, paddedWidth, paddedHeight, borderSize) {
  return _webGPU.draw(posData, colData, vertexCount, context, backgroundColor, paddedWidth, paddedHeight, borderSize);
}

;// ./src/shared/message_handler.js

const CallbackKind = {
  DATA: 1,
  ERROR: 2
};
const StreamKind = {
  CANCEL: 1,
  CANCEL_COMPLETE: 2,
  CLOSE: 3,
  ENQUEUE: 4,
  ERROR: 5,
  PULL: 6,
  PULL_COMPLETE: 7,
  START_COMPLETE: 8
};
function onFn() {}
function wrapReason(ex) {
  if (ex instanceof AbortException || ex instanceof InvalidPDFException || ex instanceof PasswordException || ex instanceof ResponseException || ex instanceof UnknownErrorException) {
    return ex;
  }
  if (typeof ex !== "object" || ex === null) {
    return new UnknownErrorException(String(ex), String(ex));
  }
  switch (ex.name) {
    case "AbortException":
      return new AbortException(ex.message);
    case "InvalidPDFException":
      return new InvalidPDFException(ex.message);
    case "PasswordException":
      return new PasswordException(ex.message, ex.code);
    case "ResponseException":
      return new ResponseException(ex.message, ex.status, ex.missing);
    case "UnknownErrorException":
      return new UnknownErrorException(ex.message, ex.details);
  }
  return new UnknownErrorException(ex.message, ex.toString());
}
class MessageHandler {
  #actions = new Map();
  #callbackCapabilities = new Map();
  #callbackId = 1;
  #comObj;
  #messageAC = new AbortController();
  #sourceName;
  #streamControllers = new Map();
  #streamId = 1;
  #streamSinks = new Map();
  #targetName;
  constructor(sourceName, targetName, comObj) {
    this.#sourceName = sourceName;
    this.#targetName = targetName;
    this.#comObj = comObj;
    comObj.addEventListener("message", this.#onMessage.bind(this), {
      signal: this.#messageAC.signal
    });
  }
  #onMessage({
    data
  }) {
    if (data.targetName !== this.#sourceName) {
      return;
    }
    if (data.stream) {
      this.#processStreamMessage(data);
      return;
    }
    if (data.callback) {
      const {
        callbackId,
        callback
      } = data;
      const capability = this.#callbackCapabilities.get(callbackId);
      if (!capability) {
        throw new Error(`Cannot resolve callback ${callbackId}`);
      }
      this.#callbackCapabilities.delete(callbackId);
      if (callback === CallbackKind.DATA) {
        capability.resolve(data.data);
      } else if (callback === CallbackKind.ERROR) {
        capability.reject(wrapReason(data.reason));
      } else {
        throw new Error("Unexpected callback case");
      }
      return;
    }
    const action = this.#actions.get(data.action);
    if (!action) {
      throw new Error(`Unknown action from worker: ${data.action}`);
    }
    if (data.callbackId) {
      const sourceName = this.#sourceName,
        targetName = data.sourceName,
        comObj = this.#comObj;
      Promise.try(action, data.data).then(result => {
        comObj.postMessage({
          sourceName,
          targetName,
          callback: CallbackKind.DATA,
          callbackId: data.callbackId,
          data: result
        });
      }).catch(reason => {
        comObj.postMessage({
          sourceName,
          targetName,
          callback: CallbackKind.ERROR,
          callbackId: data.callbackId,
          reason: wrapReason(reason)
        });
      });
      return;
    }
    if (data.streamId) {
      this.#createStreamSink(data);
      return;
    }
    action(data.data);
  }
  on(actionName, handler) {
    const ah = this.#actions;
    if (ah.has(actionName)) {
      throw new Error(`There is already a "${actionName}" handler.`);
    }
    ah.set(actionName, handler);
  }
  send(actionName, data, transfers) {
    this.#comObj.postMessage({
      sourceName: this.#sourceName,
      targetName: this.#targetName,
      action: actionName,
      data
    }, transfers);
  }
  sendWithPromise(actionName, data, transfers) {
    const callbackId = this.#callbackId++,
      capability = Promise.withResolvers();
    this.#callbackCapabilities.set(callbackId, capability);
    try {
      this.#comObj.postMessage({
        sourceName: this.#sourceName,
        targetName: this.#targetName,
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
    const streamId = this.#streamId++,
      sourceName = this.#sourceName,
      targetName = this.#targetName,
      comObj = this.#comObj;
    return new ReadableStream({
      start: controller => {
        const startCapability = Promise.withResolvers();
        this.#streamControllers.set(streamId, {
          controller,
          startCall: startCapability,
          pullCall: null,
          cancelCall: null,
          isClosed: false
        });
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
        const pullCapability = Promise.withResolvers();
        this.#streamControllers.get(streamId).pullCall = pullCapability;
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
        assert(reason instanceof Error, "cancel must have a valid reason");
        const cancelCapability = Promise.withResolvers();
        this.#streamControllers.get(streamId).cancelCall = cancelCapability;
        this.#streamControllers.get(streamId).isClosed = true;
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
  #createStreamSink(data) {
    const streamId = data.streamId,
      sourceName = this.#sourceName,
      targetName = data.sourceName,
      comObj = this.#comObj;
    const streamSinks = this.#streamSinks,
      action = this.#actions.get(data.action);
    const streamSink = {
      enqueue(chunk, size = 1, transfers) {
        if (this.isCancelled) {
          return;
        }
        const lastDesiredSize = this.desiredSize;
        this.desiredSize -= size;
        if (lastDesiredSize > 0 && this.desiredSize <= 0) {
          this.sinkCapability = Promise.withResolvers();
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
        streamSinks.delete(streamId);
      },
      error(reason) {
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
      sinkCapability: Promise.withResolvers(),
      onPull: null,
      onCancel: null,
      isCancelled: false,
      desiredSize: data.desiredSize,
      ready: null
    };
    streamSink.sinkCapability.resolve();
    streamSink.ready = streamSink.sinkCapability.promise;
    streamSinks.set(streamId, streamSink);
    Promise.try(action, data.data, streamSink).then(() => {
      comObj.postMessage({
        sourceName,
        targetName,
        stream: StreamKind.START_COMPLETE,
        streamId,
        success: true
      });
    }, reason => {
      comObj.postMessage({
        sourceName,
        targetName,
        stream: StreamKind.START_COMPLETE,
        streamId,
        reason: wrapReason(reason)
      });
    });
  }
  #processStreamMessage(data) {
    const streamId = data.streamId,
      sourceName = this.#sourceName,
      targetName = data.sourceName,
      comObj = this.#comObj;
    const streamController = this.#streamControllers.get(streamId),
      streamSink = this.#streamSinks.get(streamId);
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
        Promise.try(streamSink.onPull || onFn).then(() => {
          comObj.postMessage({
            sourceName,
            targetName,
            stream: StreamKind.PULL_COMPLETE,
            streamId,
            success: true
          });
        }, reason => {
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
        assert(streamController, "enqueue should have stream controller");
        if (streamController.isClosed) {
          break;
        }
        streamController.controller.enqueue(data.chunk);
        break;
      case StreamKind.CLOSE:
        assert(streamController, "close should have stream controller");
        if (streamController.isClosed) {
          break;
        }
        streamController.isClosed = true;
        streamController.controller.close();
        this.#deleteStreamController(streamController, streamId);
        break;
      case StreamKind.ERROR:
        assert(streamController, "error should have stream controller");
        streamController.controller.error(wrapReason(data.reason));
        this.#deleteStreamController(streamController, streamId);
        break;
      case StreamKind.CANCEL_COMPLETE:
        if (data.success) {
          streamController.cancelCall.resolve();
        } else {
          streamController.cancelCall.reject(wrapReason(data.reason));
        }
        this.#deleteStreamController(streamController, streamId);
        break;
      case StreamKind.CANCEL:
        if (!streamSink) {
          break;
        }
        const dataReason = wrapReason(data.reason);
        Promise.try(streamSink.onCancel || onFn, dataReason).then(() => {
          comObj.postMessage({
            sourceName,
            targetName,
            stream: StreamKind.CANCEL_COMPLETE,
            streamId,
            success: true
          });
        }, reason => {
          comObj.postMessage({
            sourceName,
            targetName,
            stream: StreamKind.CANCEL_COMPLETE,
            streamId,
            reason: wrapReason(reason)
          });
        });
        streamSink.sinkCapability.reject(dataReason);
        streamSink.isCancelled = true;
        this.#streamSinks.delete(streamId);
        break;
      default:
        throw new Error("Unexpected stream case");
    }
  }
  async #deleteStreamController(streamController, streamId) {
    await Promise.allSettled([streamController.startCall?.promise, streamController.pullCall?.promise, streamController.cancelCall?.promise]);
    this.#streamControllers.delete(streamId);
  }
  destroy() {
    this.#messageAC?.abort();
    this.#messageAC = null;
  }
  get destroyed() {
    return !this.#messageAC;
  }
}

;// ./src/display/binary_data_factory.js


class BaseBinaryDataFactory {
  #errorStr = Object.freeze({
    cMapUrl: "CMap",
    standardFontDataUrl: "font",
    wasmUrl: "wasm"
  });
  constructor({
    cMapUrl = null,
    standardFontDataUrl = null,
    wasmUrl = null
  }) {
    this.cMapUrl = cMapUrl;
    this.standardFontDataUrl = standardFontDataUrl;
    this.wasmUrl = wasmUrl;
  }
  async fetch({
    kind,
    filename
  }) {
    switch (kind) {
      case "cMapUrl":
      case "standardFontDataUrl":
      case "wasmUrl":
        break;
      default:
        unreachable(`Not implemented: ${kind}`);
    }
    const baseUrl = this[kind];
    if (!baseUrl) {
      throw new Error(`Ensure that the \`${kind}\` API parameter is provided.`);
    }
    const url = `${baseUrl}${filename}`;
    return this._fetch(url, kind).catch(reason => {
      throw new Error(`Unable to load ${this.#errorStr[kind]} data at: ${url}`);
    });
  }
  async _fetch(url, kind) {
    unreachable("Abstract method `_fetch` called.");
  }
}
class DOMBinaryDataFactory extends BaseBinaryDataFactory {
  async _fetch(url, kind) {
    const type = kind === "cMapUrl" && !url.endsWith(".bcmap") ? "text" : "bytes";
    const data = await fetchData(url, type);
    return data instanceof Uint8Array ? data : stringToBytes(data);
  }
}

;// ./src/display/canvas_factory.js

class BaseCanvasFactory {
  #enableHWA = false;
  constructor({
    enableHWA = false
  }) {
    this.#enableHWA = enableHWA;
  }
  create(width, height) {
    if (width <= 0 || height <= 0) {
      throw new Error("Invalid canvas size");
    }
    const canvas = this._createCanvas(width, height);
    return {
      canvas,
      context: canvas.getContext("2d", {
        willReadFrequently: !this.#enableHWA
      })
    };
  }
  reset({
    canvas
  }, width, height) {
    if (!canvas) {
      throw new Error("Canvas is not specified");
    }
    if (width <= 0 || height <= 0) {
      throw new Error("Invalid canvas size");
    }
    canvas.width = width;
    canvas.height = height;
  }
  destroy(canvasAndContext) {
    const {
      canvas
    } = canvasAndContext;
    if (!canvas) {
      throw new Error("Canvas is not specified");
    }
    canvas.width = canvas.height = 0;
    canvasAndContext.canvas = null;
    canvasAndContext.context = null;
  }
  getNoAlphaContext(canvas) {
    return canvas.getContext("2d", {
      alpha: false,
      willReadFrequently: !this.#enableHWA
    });
  }
  _createCanvas(width, height) {
    unreachable("Abstract method `_createCanvas` called.");
  }
}

;// ./src/display/filter_factory.js

class BaseFilterFactory {
  addFilter(maps) {
    return "none";
  }
  addHCMFilter(fgColor, bgColor) {
    return "none";
  }
  addAlphaFilter(map) {
    return "none";
  }
  addLuminosityFilter(map) {
    return "none";
  }
  addKnockoutFilter(alpha = 0) {
    return "none";
  }
  addHighlightHCMFilter(filterName, fgColor, bgColor, newFgColor, newBgColor) {
    return "none";
  }
  addSelectionHCMFilter(fgColor, bgColor) {
    return "none";
  }
  addSelectionFilter() {
    return "none";
  }
  createSelectionStyle(pageColors = null) {
    return null;
  }
  destroy(keepHCM = false) {}
}

;// ./src/display/node_utils.js




if (isNodeJS) {
  warn("Please use the `legacy` build in Node.js environments.");
}
async function node_utils_fetchData(url) {
  const fs = process.getBuiltinModule("fs/promises");
  const data = await fs.readFile(url);
  return new Uint8Array(data);
}
class NodeFilterFactory extends BaseFilterFactory {}
class NodeCanvasFactory extends BaseCanvasFactory {
  _createCanvas(width, height) {
    const require = process.getBuiltinModule("module").createRequire(import.meta.url);
    const canvas = require("@napi-rs/canvas");
    return canvas.createCanvas(width, height);
  }
}
class NodeBinaryDataFactory extends BaseBinaryDataFactory {
  async _fetch(url, kind) {
    return node_utils_fetchData(url);
  }
}

;// ./src/display/canvas_dependency_tracker.js



const FORCED_DEPENDENCY_LABEL = "__forcedDependency";
const {
  floor,
  ceil
} = Math;
function expandBBox(array, index, minX, minY, maxX, maxY) {
  array[index * 4 + 0] = Math.min(array[index * 4 + 0], minX);
  array[index * 4 + 1] = Math.min(array[index * 4 + 1], minY);
  array[index * 4 + 2] = Math.max(array[index * 4 + 2], maxX);
  array[index * 4 + 3] = Math.max(array[index * 4 + 3], maxY);
}
function scaleCharBBox(scaleX, scaleY, x, y, bbox) {
  let temp;
  if (scaleX) {
    if (scaleX < 0) {
      temp = bbox[0];
      bbox[0] = bbox[2];
      bbox[2] = temp;
    }
    bbox[0] *= scaleX;
    bbox[2] *= scaleX;
    if (scaleY < 0) {
      temp = bbox[1];
      bbox[1] = bbox[3];
      bbox[3] = temp;
    }
    bbox[1] *= scaleY;
    bbox[3] *= scaleY;
  } else {
    bbox.fill(0);
  }
  bbox[0] += x;
  bbox[1] += y;
  bbox[2] += x;
  bbox[3] += y;
}
const EMPTY_BBOX = new Uint32Array(new Uint8Array([255, 255, 0, 0]).buffer)[0];
class BBoxReader {
  #bboxes;
  #coords;
  constructor(bboxes, coords) {
    this.#bboxes = bboxes;
    this.#coords = coords;
  }
  static fromBuffer(buffer) {
    return new BBoxReader(new Uint32Array(buffer), new Uint8ClampedArray(buffer));
  }
  get buffer() {
    return this.#bboxes.buffer;
  }
  get length() {
    return this.#bboxes.length;
  }
  isEmpty(i) {
    return this.#bboxes[i] === EMPTY_BBOX;
  }
  minX(i) {
    return this.#coords[i * 4 + 0] / 256;
  }
  minY(i) {
    return this.#coords[i * 4 + 1] / 256;
  }
  maxX(i) {
    return (this.#coords[i * 4 + 2] + 1) / 256;
  }
  maxY(i) {
    return (this.#coords[i * 4 + 3] + 1) / 256;
  }
}
const ensureDebugMetadata = (map, key) => map?.getOrInsertComputed(key, () => ({
  dependencies: new Set(),
  isRenderingOperation: false
}));
class CanvasBBoxTracker {
  #baseTransformStack = [[1, 0, 0, 1, 0, 0]];
  #clipBox = [-Infinity, -Infinity, Infinity, Infinity];
  #pendingBBox = new Float64Array(BBOX_INIT);
  _pendingBBoxIdx = -1;
  #canvasWidth;
  #canvasHeight;
  #bboxesCoords;
  #bboxes;
  _savesStack = [];
  _markedContentStack = [];
  constructor(canvas, operationsCount) {
    this.#canvasWidth = canvas.width;
    this.#canvasHeight = canvas.height;
    this.#initializeBBoxes(operationsCount);
  }
  growOperationsCount(operationsCount) {
    if (operationsCount >= this.#bboxes.length) {
      this.#initializeBBoxes(operationsCount, this.#bboxes);
    }
  }
  #initializeBBoxes(operationsCount, oldBBoxes) {
    const buffer = new ArrayBuffer(operationsCount * 4);
    this.#bboxesCoords = new Uint8ClampedArray(buffer);
    this.#bboxes = new Uint32Array(buffer);
    if (oldBBoxes && oldBBoxes.length > 0) {
      this.#bboxes.set(oldBBoxes);
      this.#bboxes.fill(EMPTY_BBOX, oldBBoxes.length);
    } else {
      this.#bboxes.fill(EMPTY_BBOX);
    }
  }
  get clipBox() {
    return this.#clipBox;
  }
  save(opIdx) {
    this.#clipBox = {
      __proto__: this.#clipBox
    };
    this._savesStack.push(opIdx);
    return this;
  }
  restore(opIdx, onSavePopped) {
    const previous = Object.getPrototypeOf(this.#clipBox);
    if (previous === null) {
      return this;
    }
    this.#clipBox = previous;
    const lastSave = this._savesStack.pop();
    if (lastSave !== undefined) {
      onSavePopped?.(lastSave, opIdx);
      this.#bboxes[opIdx] = this.#bboxes[lastSave];
    }
    return this;
  }
  recordOpenMarker(idx) {
    this._savesStack.push(idx);
    return this;
  }
  getOpenMarker() {
    return this._savesStack.length === 0 ? null : this._savesStack.at(-1);
  }
  recordCloseMarker(opIdx, onSavePopped) {
    const lastSave = this._savesStack.pop();
    if (lastSave !== undefined) {
      onSavePopped?.(lastSave, opIdx);
      this.#bboxes[opIdx] = this.#bboxes[lastSave];
    }
    return this;
  }
  beginMarkedContent(opIdx) {
    this._markedContentStack.push(opIdx);
    return this;
  }
  endMarkedContent(opIdx, onSavePopped) {
    const lastSave = this._markedContentStack.pop();
    if (lastSave !== undefined) {
      onSavePopped?.(lastSave, opIdx);
      this.#bboxes[opIdx] = this.#bboxes[lastSave];
    }
    return this;
  }
  pushBaseTransform(ctx) {
    this.#baseTransformStack.push(Util.multiplyByDOMMatrix(this.#baseTransformStack.at(-1), ctx.getTransform()));
    return this;
  }
  popBaseTransform() {
    if (this.#baseTransformStack.length > 1) {
      this.#baseTransformStack.pop();
    }
    return this;
  }
  resetBBox(idx) {
    if (this._pendingBBoxIdx !== idx) {
      this._pendingBBoxIdx = idx;
      this.#pendingBBox.set(BBOX_INIT, 0);
    }
    return this;
  }
  recordClipBox(idx, ctx, minX, maxX, minY, maxY) {
    const transform = Util.multiplyByDOMMatrix(this.#baseTransformStack.at(-1), ctx.getTransform());
    const clipBox = BBOX_INIT.slice();
    Util.axialAlignedBoundingBox([minX, minY, maxX, maxY], transform, clipBox);
    const intersection = Util.intersect(this.#clipBox, clipBox);
    if (intersection) {
      this.#clipBox[0] = intersection[0];
      this.#clipBox[1] = intersection[1];
      this.#clipBox[2] = intersection[2];
      this.#clipBox[3] = intersection[3];
    } else {
      this.#clipBox[0] = this.#clipBox[1] = Infinity;
      this.#clipBox[2] = this.#clipBox[3] = -Infinity;
    }
    return this;
  }
  recordBBox(idx, ctx, minX, maxX, minY, maxY) {
    const clipBox = this.#clipBox;
    if (clipBox[0] === Infinity) {
      return this;
    }
    const transform = Util.multiplyByDOMMatrix(this.#baseTransformStack.at(-1), ctx.getTransform());
    if (clipBox[0] === -Infinity) {
      Util.axialAlignedBoundingBox([minX, minY, maxX, maxY], transform, this.#pendingBBox);
      return this;
    }
    const bbox = BBOX_INIT.slice();
    Util.axialAlignedBoundingBox([minX, minY, maxX, maxY], transform, bbox);
    this.#pendingBBox[0] = MathClamp(bbox[0], clipBox[0], this.#pendingBBox[0]);
    this.#pendingBBox[1] = MathClamp(bbox[1], clipBox[1], this.#pendingBBox[1]);
    this.#pendingBBox[2] = MathClamp(bbox[2], this.#pendingBBox[2], clipBox[2]);
    this.#pendingBBox[3] = MathClamp(bbox[3], this.#pendingBBox[3], clipBox[3]);
    return this;
  }
  recordFullPageBBox(idx) {
    this.#pendingBBox[0] = Math.max(0, this.#clipBox[0]);
    this.#pendingBBox[1] = Math.max(0, this.#clipBox[1]);
    this.#pendingBBox[2] = Math.min(this.#canvasWidth, this.#clipBox[2]);
    this.#pendingBBox[3] = Math.min(this.#canvasHeight, this.#clipBox[3]);
    return this;
  }
  recordOperation(idx, preserve = false, dependencyLists) {
    if (this._pendingBBoxIdx !== idx) {
      return this;
    }
    const minX = floor(this.#pendingBBox[0] * 256 / this.#canvasWidth);
    const minY = floor(this.#pendingBBox[1] * 256 / this.#canvasHeight);
    const maxX = ceil(this.#pendingBBox[2] * 256 / this.#canvasWidth);
    const maxY = ceil(this.#pendingBBox[3] * 256 / this.#canvasHeight);
    expandBBox(this.#bboxesCoords, idx, minX, minY, maxX, maxY);
    if (dependencyLists) {
      for (const dependencies of dependencyLists) {
        for (const depIdx of dependencies) {
          if (depIdx !== idx) {
            expandBBox(this.#bboxesCoords, depIdx, minX, minY, maxX, maxY);
          }
        }
      }
    }
    if (!preserve) {
      this._pendingBBoxIdx = -1;
    }
    return this;
  }
  bboxToClipBoxDropOperation(idx) {
    if (this._pendingBBoxIdx === idx) {
      this._pendingBBoxIdx = -1;
      this.#clipBox[0] = Math.max(this.#clipBox[0], this.#pendingBBox[0]);
      this.#clipBox[1] = Math.max(this.#clipBox[1], this.#pendingBBox[1]);
      this.#clipBox[2] = Math.min(this.#clipBox[2], this.#pendingBBox[2]);
      this.#clipBox[3] = Math.min(this.#clipBox[3], this.#pendingBBox[3]);
    }
    return this;
  }
  take() {
    return new BBoxReader(this.#bboxes, this.#bboxesCoords);
  }
  takeDebugMetadata() {
    throw new Error("Unreachable");
  }
  recordSimpleData(name, idx) {
    return this;
  }
  recordIncrementalData(name, idx) {
    return this;
  }
  resetIncrementalData(name, idx) {
    return this;
  }
  recordNamedData(name, idx) {
    return this;
  }
  recordSimpleDataFromNamed(name, depName, fallbackIdx) {
    return this;
  }
  recordFutureForcedDependency(name, idx) {
    return this;
  }
  inheritSimpleDataAsFutureForcedDependencies(names) {
    return this;
  }
  inheritPendingDependenciesAsFutureForcedDependencies() {
    return this;
  }
  recordCharacterBBox(idx, ctx, font, scale = 1, x = 0, y = 0, getMeasure) {
    return this;
  }
  getSimpleIndex(dependencyName) {
    return undefined;
  }
  recordDependencies(idx, dependencyNames) {
    return this;
  }
  recordNamedDependency(idx, name) {
    return this;
  }
  recordShowTextOperation(idx, preserve = false) {
    return this;
  }
}
class CanvasDependencyTracker {
  #simple = {
    __proto__: null
  };
  #incremental = {
    __proto__: null,
    transform: [],
    moveText: [],
    sameLineText: [],
    [FORCED_DEPENDENCY_LABEL]: []
  };
  #namedDependencies = new Map();
  #pendingDependencies = new Set();
  #fontBBoxTrustworthy = new Map();
  #debugMetadata;
  #recordDebugMetadataDepenencyAfterRestore;
  #bboxTracker;
  constructor(bboxTracker, recordDebugMetadata = false) {
    this.#bboxTracker = bboxTracker;
    if (recordDebugMetadata) {
      this.#debugMetadata = new Map();
      this.#recordDebugMetadataDepenencyAfterRestore = (lastSave, opIdx) => {
        ensureDebugMetadata(this.#debugMetadata, opIdx).dependencies.add(lastSave);
      };
    }
  }
  get clipBox() {
    return this.#bboxTracker.clipBox;
  }
  growOperationsCount(operationsCount) {
    this.#bboxTracker.growOperationsCount(operationsCount);
  }
  save(opIdx) {
    this.#simple = {
      __proto__: this.#simple
    };
    this.#incremental = {
      __proto__: this.#incremental,
      transform: {
        __proto__: this.#incremental.transform
      },
      moveText: {
        __proto__: this.#incremental.moveText
      },
      sameLineText: {
        __proto__: this.#incremental.sameLineText
      },
      [FORCED_DEPENDENCY_LABEL]: {
        __proto__: this.#incremental[FORCED_DEPENDENCY_LABEL]
      }
    };
    this.#bboxTracker.save(opIdx);
    return this;
  }
  restore(opIdx) {
    this.#bboxTracker.restore(opIdx, this.#recordDebugMetadataDepenencyAfterRestore);
    const previous = Object.getPrototypeOf(this.#simple);
    if (previous === null) {
      return this;
    }
    this.#simple = previous;
    this.#incremental = Object.getPrototypeOf(this.#incremental);
    return this;
  }
  recordOpenMarker(opIdx) {
    this.#bboxTracker.recordOpenMarker(opIdx, this.#recordDebugMetadataDepenencyAfterRestore);
    return this;
  }
  getOpenMarker() {
    return this.#bboxTracker.getOpenMarker();
  }
  recordCloseMarker(opIdx) {
    this.#bboxTracker.recordCloseMarker(opIdx, this.#recordDebugMetadataDepenencyAfterRestore);
    return this;
  }
  beginMarkedContent(opIdx) {
    this.#bboxTracker.beginMarkedContent(opIdx);
    return this;
  }
  endMarkedContent(opIdx) {
    this.#bboxTracker.endMarkedContent(opIdx, this.#recordDebugMetadataDepenencyAfterRestore);
    return this;
  }
  pushBaseTransform(ctx) {
    this.#bboxTracker.pushBaseTransform(ctx);
    return this;
  }
  popBaseTransform() {
    this.#bboxTracker.popBaseTransform();
    return this;
  }
  recordSimpleData(name, idx) {
    this.#simple[name] = idx;
    return this;
  }
  recordIncrementalData(name, idx) {
    this.#incremental[name].push(idx);
    return this;
  }
  resetIncrementalData(name, idx) {
    this.#incremental[name].length = 0;
    return this;
  }
  recordNamedData(name, idx) {
    this.#namedDependencies.set(name, idx);
    return this;
  }
  recordSimpleDataFromNamed(name, depName, fallbackIdx) {
    this.#simple[name] = this.#namedDependencies.get(depName) ?? fallbackIdx;
  }
  recordFutureForcedDependency(name, idx) {
    this.recordIncrementalData(FORCED_DEPENDENCY_LABEL, idx);
    return this;
  }
  inheritSimpleDataAsFutureForcedDependencies(names) {
    for (const name of names) {
      if (name in this.#simple) {
        this.recordFutureForcedDependency(name, this.#simple[name]);
      }
    }
    return this;
  }
  inheritPendingDependenciesAsFutureForcedDependencies() {
    for (const dep of this.#pendingDependencies) {
      this.recordFutureForcedDependency(FORCED_DEPENDENCY_LABEL, dep);
    }
    return this;
  }
  resetBBox(idx) {
    this.#bboxTracker.resetBBox(idx);
    return this;
  }
  recordClipBox(idx, ctx, minX, maxX, minY, maxY) {
    this.#bboxTracker.recordClipBox(idx, ctx, minX, maxX, minY, maxY);
    return this;
  }
  recordBBox(idx, ctx, minX, maxX, minY, maxY) {
    this.#bboxTracker.recordBBox(idx, ctx, minX, maxX, minY, maxY);
    return this;
  }
  recordCharacterBBox(idx, ctx, font, scale = 1, x = 0, y = 0, getMeasure) {
    const fontBBox = font.bbox;
    let isBBoxTrustworthy;
    let computedBBox;
    if (fontBBox) {
      isBBoxTrustworthy = fontBBox[2] !== fontBBox[0] && fontBBox[3] !== fontBBox[1] && this.#fontBBoxTrustworthy.get(font);
      if (isBBoxTrustworthy !== false) {
        computedBBox = [0, 0, 0, 0];
        Util.axialAlignedBoundingBox(fontBBox, font.fontMatrix, computedBBox);
        if (scale !== 1 || x !== 0 || y !== 0) {
          scaleCharBBox(scale, -scale, x, y, computedBBox);
        }
        if (isBBoxTrustworthy) {
          return this.recordBBox(idx, ctx, computedBBox[0], computedBBox[2], computedBBox[1], computedBBox[3]);
        }
      }
    }
    if (!getMeasure) {
      return this.recordFullPageBBox(idx);
    }
    const measure = getMeasure();
    if (fontBBox && computedBBox && isBBoxTrustworthy === undefined) {
      isBBoxTrustworthy = computedBBox[0] <= x - measure.actualBoundingBoxLeft && computedBBox[2] >= x + measure.actualBoundingBoxRight && computedBBox[1] <= y - measure.actualBoundingBoxAscent && computedBBox[3] >= y + measure.actualBoundingBoxDescent;
      this.#fontBBoxTrustworthy.set(font, isBBoxTrustworthy);
      if (isBBoxTrustworthy) {
        return this.recordBBox(idx, ctx, computedBBox[0], computedBBox[2], computedBBox[1], computedBBox[3]);
      }
    }
    return this.recordBBox(idx, ctx, x - measure.actualBoundingBoxLeft, x + measure.actualBoundingBoxRight, y - measure.actualBoundingBoxAscent, y + measure.actualBoundingBoxDescent);
  }
  recordFullPageBBox(idx) {
    this.#bboxTracker.recordFullPageBBox(idx);
    return this;
  }
  getSimpleIndex(dependencyName) {
    return this.#simple[dependencyName];
  }
  recordDependencies(idx, dependencyNames) {
    const pendingDependencies = this.#pendingDependencies;
    const simple = this.#simple;
    const incremental = this.#incremental;
    for (const name of dependencyNames) {
      if (name in this.#simple) {
        pendingDependencies.add(simple[name]);
      } else if (name in incremental) {
        incremental[name].forEach(pendingDependencies.add, pendingDependencies);
      }
    }
    return this;
  }
  recordNamedDependency(idx, name) {
    if (this.#namedDependencies.has(name)) {
      this.#pendingDependencies.add(this.#namedDependencies.get(name));
    }
    return this;
  }
  recordOperation(idx, preserve = false) {
    this.recordDependencies(idx, [FORCED_DEPENDENCY_LABEL]);
    if (this.#debugMetadata) {
      const metadata = ensureDebugMetadata(this.#debugMetadata, idx);
      const {
        dependencies
      } = metadata;
      this.#pendingDependencies.forEach(dependencies.add, dependencies);
      this.#bboxTracker._savesStack.forEach(dependencies.add, dependencies);
      this.#bboxTracker._markedContentStack.forEach(dependencies.add, dependencies);
      dependencies.delete(idx);
      metadata.isRenderingOperation = true;
    }
    const needsCleanup = !preserve && idx === this.#bboxTracker._pendingBBoxIdx;
    this.#bboxTracker.recordOperation(idx, preserve, [this.#pendingDependencies, this.#bboxTracker._savesStack, this.#bboxTracker._markedContentStack]);
    if (needsCleanup) {
      this.#pendingDependencies.clear();
    }
    return this;
  }
  recordShowTextOperation(idx, preserve = false) {
    const deps = Array.from(this.#pendingDependencies);
    this.recordOperation(idx, preserve);
    this.recordIncrementalData("sameLineText", idx);
    for (const dep of deps) {
      this.recordIncrementalData("sameLineText", dep);
    }
    return this;
  }
  bboxToClipBoxDropOperation(idx, preserve = false) {
    const needsCleanup = !preserve && idx === this.#bboxTracker._pendingBBoxIdx;
    this.#bboxTracker.bboxToClipBoxDropOperation(idx);
    if (needsCleanup) {
      this.#pendingDependencies.clear();
    }
    return this;
  }
  take() {
    this.#fontBBoxTrustworthy.clear();
    return this.#bboxTracker.take();
  }
  takeDebugMetadata() {
    return this.#debugMetadata;
  }
}
class CanvasNestedDependencyTracker {
  #dependencyTracker;
  #opIdx;
  #ignoreBBoxes;
  #nestingLevel = 0;
  #savesLevel = 0;
  constructor(dependencyTracker, opIdx, ignoreBBoxes) {
    if (dependencyTracker instanceof CanvasNestedDependencyTracker && dependencyTracker.#ignoreBBoxes === !!ignoreBBoxes) {
      return dependencyTracker;
    }
    this.#dependencyTracker = dependencyTracker;
    this.#opIdx = opIdx;
    this.#ignoreBBoxes = !!ignoreBBoxes;
  }
  get clipBox() {
    return this.#dependencyTracker.clipBox;
  }
  growOperationsCount() {
    throw new Error("Unreachable");
  }
  save(opIdx) {
    this.#savesLevel++;
    this.#dependencyTracker.save(this.#opIdx);
    return this;
  }
  restore(opIdx) {
    if (this.#savesLevel > 0) {
      this.#dependencyTracker.restore(this.#opIdx);
      this.#savesLevel--;
    }
    return this;
  }
  recordOpenMarker(idx) {
    this.#nestingLevel++;
    return this;
  }
  getOpenMarker() {
    return this.#nestingLevel > 0 ? this.#opIdx : this.#dependencyTracker.getOpenMarker();
  }
  recordCloseMarker(idx) {
    this.#nestingLevel--;
    return this;
  }
  beginMarkedContent(opIdx) {
    return this;
  }
  endMarkedContent(opIdx) {
    return this;
  }
  pushBaseTransform(ctx) {
    this.#dependencyTracker.pushBaseTransform(ctx);
    return this;
  }
  popBaseTransform() {
    this.#dependencyTracker.popBaseTransform();
    return this;
  }
  recordSimpleData(name, idx) {
    this.#dependencyTracker.recordSimpleData(name, this.#opIdx);
    return this;
  }
  recordIncrementalData(name, idx) {
    this.#dependencyTracker.recordIncrementalData(name, this.#opIdx);
    return this;
  }
  resetIncrementalData(name, idx) {
    this.#dependencyTracker.resetIncrementalData(name, this.#opIdx);
    return this;
  }
  recordNamedData(name, idx) {
    return this;
  }
  recordSimpleDataFromNamed(name, depName, fallbackIdx) {
    this.#dependencyTracker.recordSimpleDataFromNamed(name, depName, this.#opIdx);
    return this;
  }
  recordFutureForcedDependency(name, idx) {
    this.#dependencyTracker.recordFutureForcedDependency(name, this.#opIdx);
    return this;
  }
  inheritSimpleDataAsFutureForcedDependencies(names) {
    this.#dependencyTracker.inheritSimpleDataAsFutureForcedDependencies(names);
    return this;
  }
  inheritPendingDependenciesAsFutureForcedDependencies() {
    this.#dependencyTracker.inheritPendingDependenciesAsFutureForcedDependencies();
    return this;
  }
  resetBBox(idx) {
    if (!this.#ignoreBBoxes) {
      this.#dependencyTracker.resetBBox(this.#opIdx);
    }
    return this;
  }
  recordClipBox(idx, ctx, minX, maxX, minY, maxY) {
    if (!this.#ignoreBBoxes) {
      this.#dependencyTracker.recordClipBox(this.#opIdx, ctx, minX, maxX, minY, maxY);
    }
    return this;
  }
  recordBBox(idx, ctx, minX, maxX, minY, maxY) {
    if (!this.#ignoreBBoxes) {
      this.#dependencyTracker.recordBBox(this.#opIdx, ctx, minX, maxX, minY, maxY);
    }
    return this;
  }
  recordCharacterBBox(idx, ctx, font, scale, x, y, getMeasure) {
    if (!this.#ignoreBBoxes) {
      this.#dependencyTracker.recordCharacterBBox(this.#opIdx, ctx, font, scale, x, y, getMeasure);
    }
    return this;
  }
  recordFullPageBBox(idx) {
    if (!this.#ignoreBBoxes) {
      this.#dependencyTracker.recordFullPageBBox(this.#opIdx);
    }
    return this;
  }
  getSimpleIndex(dependencyName) {
    return this.#dependencyTracker.getSimpleIndex(dependencyName);
  }
  recordDependencies(idx, dependencyNames) {
    this.#dependencyTracker.recordDependencies(this.#opIdx, dependencyNames);
    return this;
  }
  recordNamedDependency(idx, name) {
    this.#dependencyTracker.recordNamedDependency(this.#opIdx, name);
    return this;
  }
  recordOperation(idx) {
    this.#dependencyTracker.recordOperation(this.#opIdx, true);
    return this;
  }
  recordShowTextOperation(idx) {
    this.#dependencyTracker.recordShowTextOperation(this.#opIdx, true);
    return this;
  }
  bboxToClipBoxDropOperation(idx) {
    if (!this.#ignoreBBoxes) {
      this.#dependencyTracker.bboxToClipBoxDropOperation(this.#opIdx, true);
    }
    return this;
  }
  take() {
    throw new Error("Unreachable");
  }
  takeDebugMetadata() {
    throw new Error("Unreachable");
  }
}
const Dependencies = {
  stroke: ["path", "transform", "filter", "strokeColor", "strokeAlpha", "lineWidth", "lineCap", "lineJoin", "miterLimit", "dash"],
  fill: ["path", "transform", "filter", "fillColor", "fillAlpha", "globalCompositeOperation", "SMask"],
  imageXObject: ["transform", "SMask", "filter", "fillAlpha", "strokeAlpha", "globalCompositeOperation"],
  rawFillPath: ["filter", "fillColor", "fillAlpha"],
  showText: ["transform", "leading", "charSpacing", "wordSpacing", "hScale", "textRise", "moveText", "textMatrix", "font", "fontObj", "filter", "fillColor", "textRenderingMode", "SMask", "fillAlpha", "strokeAlpha", "globalCompositeOperation", "sameLineText"],
  transform: ["transform"],
  transformAndFill: ["transform", "filter", "fillColor"]
};
class CanvasImagesTracker {
  #canvasWidth;
  #canvasHeight;
  #capacity = 4;
  #count = 0;
  #coords = new CanvasImagesTracker.#CoordsArray(this.#capacity * 6);
  static #CoordsArray = FeatureTest.isFloat16ArraySupported ? Float16Array : Float32Array;
  constructor(canvas) {
    this.#canvasWidth = canvas.width;
    this.#canvasHeight = canvas.height;
  }
  record(ctx, width, height, clipBox) {
    if (this.#count === this.#capacity) {
      this.#capacity *= 2;
      const newCoords = new CanvasImagesTracker.#CoordsArray(this.#capacity * 6);
      newCoords.set(this.#coords);
      this.#coords = newCoords;
    }
    const transform = getCurrentTransform(ctx);
    let coords;
    if (clipBox[0] !== Infinity) {
      const bbox = BBOX_INIT.slice();
      Util.axialAlignedBoundingBox([0, -height, width, 0], transform, bbox);
      const finalBBox = Util.intersect(clipBox, bbox);
      if (!finalBBox) {
        return;
      }
      const [minX, minY, maxX, maxY] = finalBBox;
      if (minX !== bbox[0] || minY !== bbox[1] || maxX !== bbox[2] || maxY !== bbox[3]) {
        const rotationAngle = Math.atan2(transform[1], transform[0]);
        const sin = Math.abs(Math.sin(rotationAngle));
        const cos = Math.abs(Math.cos(rotationAngle));
        if (sin < 1e-6 || cos < 1e-6 || Math.abs(sin - cos) < 1e-6) {
          coords = [minX, minY, minX, maxY, maxX, minY];
        } else {
          const finalBBoxWidth = maxX - minX;
          const finalBBoxHeight = maxY - minY;
          const sin2 = sin * sin;
          const cos2 = cos * cos;
          const cosSin = cos * sin;
          const denom = cos2 - sin2;
          const a = (finalBBoxHeight * cos2 - finalBBoxWidth * cosSin) / denom;
          const b = (finalBBoxHeight * cosSin - finalBBoxWidth * sin2) / denom;
          coords = [minX + b, minY, minX, minY + a, maxX, maxY - a];
        }
      }
    }
    if (!coords) {
      coords = [0, -height, 0, 0, width, -height];
      Util.applyTransform(coords, transform, 0);
      Util.applyTransform(coords, transform, 2);
      Util.applyTransform(coords, transform, 4);
    }
    coords[0] /= this.#canvasWidth;
    coords[1] /= this.#canvasHeight;
    coords[2] /= this.#canvasWidth;
    coords[3] /= this.#canvasHeight;
    coords[4] /= this.#canvasWidth;
    coords[5] /= this.#canvasHeight;
    this.#coords.set(coords, this.#count * 6);
    this.#count++;
  }
  take() {
    return this.#coords.subarray(0, this.#count * 6);
  }
}
function createCanvasTrackers(canvas, operationsCount, {
  recordOperations = false,
  recordImages = false,
  recordDebugMetadata = false
}) {
  const bboxTracker = recordOperations || recordImages ? new CanvasBBoxTracker(canvas, operationsCount) : null;
  return {
    dependencyTracker: recordOperations ? new CanvasDependencyTracker(bboxTracker, recordDebugMetadata) : bboxTracker,
    imagesTracker: recordImages ? new CanvasImagesTracker(canvas) : null
  };
}

;// ./src/shared/image_utils.js
/* unused harmony import specifier */ var image_utils_ImageKind;
/* unused harmony import specifier */ var image_utils_FeatureTest;


function convertToRGBA(params) {
  switch (params.kind) {
    case image_utils_ImageKind.GRAYSCALE_1BPP:
      return convertBlackAndWhiteToRGBA(params);
    case image_utils_ImageKind.RGB_24BPP:
      return convertRGBToRGBA(params);
  }
  return null;
}
function convertBlackAndWhiteToRGBA({
  src,
  srcPos = 0,
  dest,
  width,
  height,
  nonBlackColor = 0xffffffff,
  inverseDecode = false
}) {
  const black = FeatureTest.isLittleEndian ? 0xff000000 : 0x000000ff;
  const [zeroMapping, oneMapping] = inverseDecode ? [nonBlackColor, black] : [black, nonBlackColor];
  const widthInSource = width >> 3;
  const widthRemainder = width & 7;
  const xorMask = zeroMapping ^ oneMapping;
  const srcLength = src.length;
  dest = new Uint32Array(dest.buffer);
  let destPos = 0;
  for (let i = 0; i < height; ++i) {
    for (const max = srcPos + widthInSource; srcPos < max; ++srcPos, destPos += 8) {
      const elem = src[srcPos];
      dest[destPos] = zeroMapping ^ -(elem >> 7 & 1) & xorMask;
      dest[destPos + 1] = zeroMapping ^ -(elem >> 6 & 1) & xorMask;
      dest[destPos + 2] = zeroMapping ^ -(elem >> 5 & 1) & xorMask;
      dest[destPos + 3] = zeroMapping ^ -(elem >> 4 & 1) & xorMask;
      dest[destPos + 4] = zeroMapping ^ -(elem >> 3 & 1) & xorMask;
      dest[destPos + 5] = zeroMapping ^ -(elem >> 2 & 1) & xorMask;
      dest[destPos + 6] = zeroMapping ^ -(elem >> 1 & 1) & xorMask;
      dest[destPos + 7] = zeroMapping ^ -(elem & 1) & xorMask;
    }
    if (widthRemainder === 0) {
      continue;
    }
    const elem = srcPos < srcLength ? src[srcPos++] : 255;
    for (let j = 0; j < widthRemainder; ++j, ++destPos) {
      dest[destPos] = zeroMapping ^ -(elem >> 7 - j & 1) & xorMask;
    }
  }
  return {
    srcPos,
    destPos
  };
}
function convertRGBToRGBA({
  src,
  srcPos = 0,
  dest,
  destPos = 0,
  width,
  height
}) {
  let i = 0;
  const len = width * height * 3;
  const byteOffset = src.byteOffset + srcPos;
  const len32 = byteOffset % 4 === 0 ? Math.floor(MathClamp(src.length - srcPos, 0, len) / 4) : 0;
  const src32 = len32 > 0 ? new Uint32Array(src.buffer, byteOffset, len32) : null;
  const alphaMask = FeatureTest.isLittleEndian ? 0xff000000 : 0xff;
  if (FeatureTest.isLittleEndian) {
    for (; i < len32 - 2; i += 3, destPos += 4) {
      const s1 = src32[i],
        s2 = src32[i + 1],
        s3 = src32[i + 2];
      dest[destPos] = s1 | alphaMask;
      dest[destPos + 1] = s1 >>> 24 | s2 << 8 | alphaMask;
      dest[destPos + 2] = s2 >>> 16 | s3 << 16 | alphaMask;
      dest[destPos + 3] = s3 >>> 8 | alphaMask;
    }
    for (let j = srcPos + i * 4, jj = srcPos + len; j < jj; j += 3) {
      dest[destPos++] = src[j] | src[j + 1] << 8 | src[j + 2] << 16 | alphaMask;
    }
  } else {
    for (; i < len32 - 2; i += 3, destPos += 4) {
      const s1 = src32[i],
        s2 = src32[i + 1],
        s3 = src32[i + 2];
      dest[destPos] = s1 | alphaMask;
      dest[destPos + 1] = s1 << 24 | s2 >>> 8 | alphaMask;
      dest[destPos + 2] = s2 << 16 | s3 >>> 16 | alphaMask;
      dest[destPos + 3] = s3 << 8 | alphaMask;
    }
    for (let j = srcPos + i * 4, jj = srcPos + len; j < jj; j += 3) {
      dest[destPos++] = src[j] << 24 | src[j + 1] << 16 | src[j + 2] << 8 | alphaMask;
    }
  }
  return {
    srcPos: srcPos + len,
    destPos
  };
}
function grayToRGBA(src, dest) {
  if (image_utils_FeatureTest.isLittleEndian) {
    for (let i = 0, ii = src.length; i < ii; i++) {
      dest[i] = src[i] * 0x10101 | 0xff000000;
    }
  } else {
    for (let i = 0, ii = src.length; i < ii; i++) {
      dest[i] = src[i] * 0x1010100 | 0x000000ff;
    }
  }
}

;// ./src/display/pattern_helper.js




const PathType = {
  FILL: "Fill",
  STROKE: "Stroke",
  SHADING: "Shading"
};
function applyBoundingBox(ctx, bbox) {
  if (!bbox) {
    return;
  }
  const width = bbox[2] - bbox[0];
  const height = bbox[3] - bbox[1];
  const region = new Path2D();
  region.rect(bbox[0], bbox[1], width, height);
  ctx.clip(region);
}
class BaseShadingPattern {
  matrix = null;
  isModifyingCurrentTransform() {
    return false;
  }
  getPattern() {
    unreachable("Abstract method `getPattern` called.");
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
  }
  isOriginBased() {
    return this._p0[0] === 0 && this._p0[1] === 0 && (!this.isRadial() || this._p1[0] === 0 && this._p1[1] === 0);
  }
  isRadial() {
    return this._type === "radial";
  }
  areConic() {
    if (!this.isRadial()) {
      return false;
    }
    const dist = Math.hypot(this._p0[0] - this._p1[0], this._p0[1] - this._p1[1]);
    return dist + this._r1 > this._r0 && dist + this._r0 > this._r1;
  }
  _createGradient(ctx, transform = null) {
    let grad;
    let firstPoint = this._p0;
    let secondPoint = this._p1;
    if (transform) {
      firstPoint = firstPoint.slice();
      secondPoint = secondPoint.slice();
      Util.applyTransform(firstPoint, transform);
      Util.applyTransform(secondPoint, transform);
    }
    if (this._type === "axial") {
      grad = ctx.createLinearGradient(firstPoint[0], firstPoint[1], secondPoint[0], secondPoint[1]);
    } else if (this._type === "radial") {
      let r0 = this._r0;
      let r1 = this._r1;
      if (transform) {
        const scale = new Float32Array(2);
        Util.singularValueDecompose2dScale(transform, scale);
        r0 *= scale[0];
        r1 *= scale[0];
      }
      grad = ctx.createRadialGradient(firstPoint[0], firstPoint[1], r0, secondPoint[0], secondPoint[1], r1);
    }
    for (const colorStop of this._colorStops) {
      grad.addColorStop(colorStop[0], colorStop[1]);
    }
    return grad;
  }
  _createReversedGradient(ctx, transform = null) {
    let firstPoint = this._p1;
    let secondPoint = this._p0;
    if (transform) {
      firstPoint = firstPoint.slice();
      secondPoint = secondPoint.slice();
      Util.applyTransform(firstPoint, transform);
      Util.applyTransform(secondPoint, transform);
    }
    let r0 = this._r1;
    let r1 = this._r0;
    if (transform) {
      const scale = new Float32Array(2);
      Util.singularValueDecompose2dScale(transform, scale);
      r0 *= scale[0];
      r1 *= scale[0];
    }
    const grad = ctx.createRadialGradient(firstPoint[0], firstPoint[1], r0, secondPoint[0], secondPoint[1], r1);
    const reversedStops = this._colorStops.map(([t, c]) => [1 - t, c]).reverse();
    for (const [t, c] of reversedStops) {
      grad.addColorStop(t, c);
    }
    return grad;
  }
  _createRasterPattern(ctx, owner, inverse, bbox, transform, transferMaps) {
    const width = Math.ceil(bbox[2] - bbox[0]) || 1;
    const height = Math.ceil(bbox[3] - bbox[1]) || 1;
    const tmpCanvas = owner.canvasFactory.create(width, height);
    const tmpCtx = tmpCanvas.context;
    tmpCtx.clearRect(0, 0, width, height);
    tmpCtx.beginPath();
    tmpCtx.rect(0, 0, width, height);
    tmpCtx.translate(-bbox[0], -bbox[1]);
    inverse = Util.transform(inverse, [1, 0, 0, 1, bbox[0], bbox[1]]);
    tmpCtx.transform(...transform);
    applyBoundingBox(tmpCtx, this._bbox);
    if (this.areConic()) {
      tmpCtx.fillStyle = this._createReversedGradient(tmpCtx);
      tmpCtx.fill();
    }
    tmpCtx.fillStyle = this._createGradient(tmpCtx);
    tmpCtx.fill();
    transferMaps?.applyToCanvas(tmpCtx);
    const pattern = ctx.createPattern(tmpCanvas.canvas, "no-repeat");
    owner.canvasFactory.destroy(tmpCanvas);
    pattern.setTransform(new DOMMatrix(inverse));
    return pattern;
  }
  getPattern(ctx, owner, inverse, pathType) {
    const transferMaps = owner.current.transferMapsFallback;
    if (pathType === PathType.STROKE || pathType === PathType.FILL) {
      if (this.isOriginBased() && !transferMaps) {
        let transf = Util.transform(inverse, owner.baseTransform);
        if (this.matrix) {
          transf = Util.transform(transf, this.matrix);
        }
        const precision = 1e-3;
        const n1 = Math.hypot(transf[0], transf[1]);
        const n2 = Math.hypot(transf[2], transf[3]);
        const ps = (transf[0] * transf[2] + transf[1] * transf[3]) / (n1 * n2);
        if (Math.abs(ps) < precision) {
          if (this.isRadial()) {
            if (Math.abs(n1 - n2) < precision) {
              return this._createGradient(ctx, transf);
            }
          } else {
            return this._createGradient(ctx, transf);
          }
        }
      }
      const ownerBBox = owner.current.getClippedPathBoundingBox(pathType, getCurrentTransform(ctx)) || [0, 0, 0, 0];
      const transform = this.matrix ? Util.transform(owner.baseTransform, this.matrix) : owner.baseTransform;
      return this._createRasterPattern(ctx, owner, inverse, ownerBBox, transform, transferMaps);
    }
    if (transferMaps && inverse) {
      return this._createRasterPattern(ctx, owner, inverse, owner.current.clipBox, getCurrentTransform(ctx), transferMaps);
    }
    if (this.areConic()) {
      ctx.save();
      applyBoundingBox(ctx, this._bbox);
      ctx.fillStyle = this._createReversedGradient(ctx);
      ctx.fillRect(-1e10, -1e10, 2e10, 2e10);
      ctx.restore();
    }
    applyBoundingBox(ctx, this._bbox);
    return this._createGradient(ctx);
  }
}
function drawTriangle(data, context, p1, p2, p3, c1, c2, c3) {
  const coords = context.coords,
    colors = context.colors;
  const bytes = data.data,
    rowSize = data.width * 4;
  let tmp;
  if (coords[p1 * 2 + 1] > coords[p2 * 2 + 1]) {
    tmp = p1;
    p1 = p2;
    p2 = tmp;
    tmp = c1;
    c1 = c2;
    c2 = tmp;
  }
  if (coords[p2 * 2 + 1] > coords[p3 * 2 + 1]) {
    tmp = p2;
    p2 = p3;
    p3 = tmp;
    tmp = c2;
    c2 = c3;
    c3 = tmp;
  }
  if (coords[p1 * 2 + 1] > coords[p2 * 2 + 1]) {
    tmp = p1;
    p1 = p2;
    p2 = tmp;
    tmp = c1;
    c1 = c2;
    c2 = tmp;
  }
  const x1 = (coords[p1 * 2] + context.offsetX) * context.scaleX;
  const y1 = (coords[p1 * 2 + 1] + context.offsetY) * context.scaleY;
  const x2 = (coords[p2 * 2] + context.offsetX) * context.scaleX;
  const y2 = (coords[p2 * 2 + 1] + context.offsetY) * context.scaleY;
  const x3 = (coords[p3 * 2] + context.offsetX) * context.scaleX;
  const y3 = (coords[p3 * 2 + 1] + context.offsetY) * context.scaleY;
  if (y1 >= y3) {
    return;
  }
  const c1r = colors[c1 * 4],
    c1g = colors[c1 * 4 + 1],
    c1b = colors[c1 * 4 + 2];
  const c2r = colors[c2 * 4],
    c2g = colors[c2 * 4 + 1],
    c2b = colors[c2 * 4 + 2];
  const c3r = colors[c3 * 4],
    c3g = colors[c3 * 4 + 1],
    c3b = colors[c3 * 4 + 2];
  const minY = Math.round(y1),
    maxY = Math.round(y3);
  let xa, car, cag, cab;
  let xb, cbr, cbg, cbb;
  for (let y = minY; y <= maxY; y++) {
    if (y < y2) {
      const k = y < y1 ? 0 : (y1 - y) / (y1 - y2);
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
class MeshShadingPattern extends BaseShadingPattern {
  constructor(IR) {
    super();
    this._posData = IR[2];
    this._colData = IR[3];
    this._vertexCount = IR[4];
    this._bounds = IR[5];
    this._bbox = IR[6];
    this._background = IR[7];
    loadMeshShader();
  }
  _createMeshCanvas(combinedScale, backgroundColor, canvasFactory, transferMaps = null) {
    const EXPECTED_SCALE = 1.1;
    const MAX_PATTERN_SIZE = 3000;
    const BORDER_SIZE = 2;
    const offsetX = Math.floor(this._bounds[0]);
    const offsetY = Math.floor(this._bounds[1]);
    const boundsWidth = Math.ceil(this._bounds[2]) - offsetX;
    const boundsHeight = Math.ceil(this._bounds[3]) - offsetY;
    const width = Math.min(Math.ceil(Math.abs(boundsWidth * combinedScale[0] * EXPECTED_SCALE)), MAX_PATTERN_SIZE) || 1;
    const height = Math.min(Math.ceil(Math.abs(boundsHeight * combinedScale[1] * EXPECTED_SCALE)), MAX_PATTERN_SIZE) || 1;
    const scaleX = boundsWidth ? boundsWidth / width : 1;
    const scaleY = boundsHeight ? boundsHeight / height : 1;
    const context = {
      coords: this._posData,
      colors: this._colData,
      offsetX: -offsetX,
      offsetY: -offsetY,
      scaleX: 1 / scaleX,
      scaleY: 1 / scaleY
    };
    const paddedWidth = width + BORDER_SIZE * 2;
    const paddedHeight = height + BORDER_SIZE * 2;
    const tmpCanvas = canvasFactory.create(paddedWidth, paddedHeight);
    if (isGPUReady() && this._vertexCount > 48) {
      tmpCanvas.context.drawImage(drawMeshWithGPU(this._posData, this._colData, this._vertexCount, context, backgroundColor, paddedWidth, paddedHeight, BORDER_SIZE), 0, 0);
    } else {
      const data = tmpCanvas.context.createImageData(width, height);
      if (backgroundColor) {
        const bytes = data.data;
        for (let i = 0, ii = bytes.length; i < ii; i += 4) {
          bytes[i] = backgroundColor[0];
          bytes[i + 1] = backgroundColor[1];
          bytes[i + 2] = backgroundColor[2];
          bytes[i + 3] = 255;
        }
      }
      for (let i = 0, ii = this._vertexCount; i < ii; i += 3) {
        drawTriangle(data, context, i, i + 1, i + 2, i, i + 1, i + 2);
      }
      tmpCanvas.context.putImageData(data, BORDER_SIZE, BORDER_SIZE);
    }
    transferMaps?.applyToCanvas(tmpCanvas.context);
    return {
      canvas: tmpCanvas.canvas,
      offsetX: offsetX - BORDER_SIZE * scaleX,
      offsetY: offsetY - BORDER_SIZE * scaleY,
      scaleX,
      scaleY
    };
  }
  isModifyingCurrentTransform() {
    return true;
  }
  getPattern(ctx, owner, inverse, pathType) {
    applyBoundingBox(ctx, this._bbox);
    const scale = new Float32Array(2);
    if (pathType === PathType.SHADING) {
      Util.singularValueDecompose2dScale(getCurrentTransform(ctx), scale);
    } else if (this.matrix) {
      Util.singularValueDecompose2dScale(this.matrix, scale);
      const [matrixScaleX, matrixScaleY] = scale;
      Util.singularValueDecompose2dScale(owner.baseTransform, scale);
      scale[0] *= matrixScaleX;
      scale[1] *= matrixScaleY;
    } else {
      Util.singularValueDecompose2dScale(owner.baseTransform, scale);
    }
    const temporaryPatternCanvas = this._createMeshCanvas(scale, pathType === PathType.SHADING ? null : this._background, owner.canvasFactory, owner.current.transferMapsFallback);
    if (pathType !== PathType.SHADING) {
      ctx.setTransform(...owner.baseTransform);
      if (this.matrix) {
        ctx.transform(...this.matrix);
      }
    }
    ctx.translate(temporaryPatternCanvas.offsetX, temporaryPatternCanvas.offsetY);
    ctx.scale(temporaryPatternCanvas.scaleX, temporaryPatternCanvas.scaleY);
    const pattern = ctx.createPattern(temporaryPatternCanvas.canvas, "no-repeat");
    owner.canvasFactory.destroy(temporaryPatternCanvas);
    return pattern;
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
  static MAX_PATTERN_SIZE = 3000;
  constructor(IR, ctx, canvasGraphicsFactory, baseTransform) {
    this.color = IR[1];
    this.operatorList = IR[2];
    this.matrix = IR[3];
    this.bbox = IR[4];
    this.xstep = IR[5];
    this.ystep = IR[6];
    this.paintType = IR[7];
    this.tilingType = IR[8];
    this.needsIsolation = IR[9] ?? true;
    this.ctx = ctx;
    this.canvasGraphicsFactory = canvasGraphicsFactory;
    this.baseTransform = baseTransform;
    this.patternBaseMatrix = this.matrix ? Util.transform(baseTransform, this.matrix) : baseTransform;
  }
  canSkipPatternCanvas([width, height, offsetX, offsetY]) {
    const [x0, y0, x1, y1] = this.bbox;
    const absXStep = Math.abs(this.xstep);
    const absYStep = Math.abs(this.ystep);
    if (width > absXStep + 1e-6 || height > absYStep + 1e-6) {
      return null;
    }
    const nXFirst = Math.floor((offsetX - x1) / absXStep) + 1;
    const nXLast = Math.ceil((offsetX + width - x0) / absXStep) - 1;
    const nYFirst = Math.floor((offsetY - y1) / absYStep) + 1;
    const nYLast = Math.ceil((offsetY + height - y0) / absYStep) - 1;
    return nXLast <= nXFirst && nYLast <= nYFirst ? [nXFirst, nYFirst] : null;
  }
  updatePatternDims(clippedBBox, dims) {
    const bbox = BBOX_INIT.slice();
    Util.axialAlignedBoundingBox(clippedBBox, Util.inverseTransform(this.patternBaseMatrix), bbox);
    dims[0] = bbox[2] - bbox[0];
    dims[1] = bbox[3] - bbox[1];
    dims[2] = bbox[0];
    dims[3] = bbox[1];
  }
  _renderTileCanvas(owner, opIdx, dimx, dimy) {
    const [x0, y0, x1, y1] = this.bbox;
    const tmpCanvas = owner.canvasFactory.create(dimx.size, dimy.size);
    const tmpCtx = tmpCanvas.context;
    const graphics = this.canvasGraphicsFactory.createCanvasGraphics(tmpCtx, opIdx);
    graphics.groupLevel = owner.groupLevel;
    graphics.current.transferMapsFallback = owner.current.transferMapsFallback;
    this.setFillAndStrokeStyleToContext(graphics, this.paintType, this.color);
    tmpCtx.translate(-dimx.scale * x0, -dimy.scale * y0);
    graphics.transform(0, dimx.scale, 0, 0, dimy.scale, 0, 0);
    tmpCtx.save();
    graphics.dependencyTracker?.save();
    this.clipBbox(graphics, x0, y0, x1, y1);
    graphics.baseTransform = getCurrentTransform(graphics.ctx);
    graphics.executeOperatorList(this.operatorList);
    graphics.endDrawing();
    graphics.dependencyTracker?.restore();
    tmpCtx.restore();
    return tmpCanvas;
  }
  _getCombinedScales() {
    const scale = new Float32Array(2);
    Util.singularValueDecompose2dScale(this.matrix, scale);
    const [matrixScaleX, matrixScaleY] = scale;
    Util.singularValueDecompose2dScale(this.baseTransform, scale);
    return [matrixScaleX * scale[0], matrixScaleY * scale[1]];
  }
  drawPattern(owner, path, useEOFill = false, [n, m], opIdx) {
    const [x0, y0, x1, y1] = this.bbox;
    const dependencyTracker = owner.dependencyTracker;
    if (dependencyTracker) {
      owner.dependencyTracker = new CanvasNestedDependencyTracker(dependencyTracker, opIdx);
    }
    try {
      owner.save();
      if (useEOFill) {
        owner.ctx.clip(path, "evenodd");
      } else {
        owner.ctx.clip(path);
      }
      owner.ctx.setTransform(...this.patternBaseMatrix);
      owner.ctx.translate(n * this.xstep, m * this.ystep);
      if (this.needsIsolation || owner.ctx.globalAlpha !== 1 || owner.ctx.globalCompositeOperation !== "source-over" || owner.inSMaskMode) {
        const bboxWidth = x1 - x0;
        const bboxHeight = y1 - y0;
        const [combinedScaleX, combinedScaleY] = this._getCombinedScales();
        const dimx = this.getSizeAndScale(bboxWidth, this.ctx.canvas.width, combinedScaleX);
        const dimy = this.getSizeAndScale(bboxHeight, this.ctx.canvas.height, combinedScaleY);
        const tmpCanvas = this._renderTileCanvas(owner, opIdx, dimx, dimy);
        owner.ctx.drawImage(tmpCanvas.canvas, x0, y0, bboxWidth, bboxHeight);
        owner.canvasFactory.destroy(tmpCanvas);
      } else {
        owner.resetGraphicsState();
        this.setFillAndStrokeStyleToContext(owner, this.paintType, this.color);
        this.clipBbox(owner, x0, y0, x1, y1);
        owner.baseTransformStack.push(owner.baseTransform);
        owner.baseTransform = getCurrentTransform(owner.ctx);
        owner.executeOperatorList(this.operatorList);
        owner.baseTransform = owner.baseTransformStack.pop();
      }
      owner.restore();
    } finally {
      if (dependencyTracker) {
        owner.dependencyTracker = dependencyTracker;
      }
    }
  }
  createPatternCanvas(owner, opIdx) {
    const [x0, y0, x1, y1] = this.bbox;
    const width = x1 - x0;
    const height = y1 - y0;
    let {
      xstep,
      ystep
    } = this;
    xstep = Math.abs(xstep);
    ystep = Math.abs(ystep);
    info("TilingType: " + this.tilingType);
    const [combinedScaleX, combinedScaleY] = this._getCombinedScales();
    let canvasWidth = width,
      canvasHeight = height,
      redrawHorizontally = false,
      redrawVertically = false;
    if (Math.ceil(xstep * combinedScaleX) >= Math.ceil(width * combinedScaleX)) {
      canvasWidth = xstep;
    } else {
      redrawHorizontally = true;
    }
    if (Math.ceil(ystep * combinedScaleY) >= Math.ceil(height * combinedScaleY)) {
      canvasHeight = ystep;
    } else {
      redrawVertically = true;
    }
    const dimx = this.getSizeAndScale(canvasWidth, this.ctx.canvas.width, combinedScaleX);
    const dimy = this.getSizeAndScale(canvasHeight, this.ctx.canvas.height, combinedScaleY);
    const tmpCanvas = this._renderTileCanvas(owner, opIdx, dimx, dimy);
    if (redrawHorizontally || redrawVertically) {
      const image = tmpCanvas.canvas;
      if (redrawHorizontally) {
        canvasWidth = xstep;
      }
      if (redrawVertically) {
        canvasHeight = ystep;
      }
      const dimx2 = this.getSizeAndScale(canvasWidth, this.ctx.canvas.width, combinedScaleX);
      const dimy2 = this.getSizeAndScale(canvasHeight, this.ctx.canvas.height, combinedScaleY);
      const xSize = dimx2.size;
      const ySize = dimy2.size;
      const tmpCanvas2 = owner.canvasFactory.create(xSize, ySize);
      const tmpCtx2 = tmpCanvas2.context;
      const ii = redrawHorizontally ? Math.min(Math.floor(width / xstep), Math.ceil(image.width / xSize)) : 0;
      const jj = redrawVertically ? Math.min(Math.floor(height / ystep), Math.ceil(image.height / ySize)) : 0;
      let rowSource = image;
      let bandCanvas = null;
      if (redrawVertically) {
        bandCanvas = owner.canvasFactory.create(image.width, ySize);
        const bandCtx = bandCanvas.context;
        for (let j = jj; j >= 0; j--) {
          bandCtx.drawImage(image, 0, ySize * j, image.width, ySize, 0, 0, image.width, ySize);
        }
        rowSource = bandCanvas.canvas;
      }
      for (let i = ii; i >= 0; i--) {
        tmpCtx2.drawImage(rowSource, xSize * i, 0, xSize, ySize, 0, 0, xSize, ySize);
      }
      if (bandCanvas) {
        owner.canvasFactory.destroy(bandCanvas);
      }
      owner.canvasFactory.destroy(tmpCanvas);
      return {
        canvas: tmpCanvas2.canvas,
        canvasEntry: tmpCanvas2,
        scaleX: dimx2.scale,
        scaleY: dimy2.scale,
        offsetX: x0,
        offsetY: y0
      };
    }
    return {
      canvas: tmpCanvas.canvas,
      canvasEntry: tmpCanvas,
      scaleX: dimx.scale,
      scaleY: dimy.scale,
      offsetX: x0,
      offsetY: y0
    };
  }
  getSizeAndScale(step, realOutputSize, scale) {
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
    const clip = new Path2D();
    clip.rect(x0, y0, bboxWidth, bboxHeight);
    Util.axialAlignedBoundingBox([x0, y0, x1, y1], getCurrentTransform(graphics.ctx), graphics.current.minMax);
    graphics.ctx.clip(clip);
    graphics.current.updateClipFromPath();
  }
  setFillAndStrokeStyleToContext(graphics, paintType, color) {
    switch (paintType) {
      case PaintType.COLORED:
        color = "#000000";
        break;
      case PaintType.UNCOLORED:
        break;
      default:
        throw new FormatError(`Unsupported paint type: ${paintType}`);
    }
    const {
      ctx,
      current
    } = graphics;
    current.patternFill = current.patternStroke = false;
    ctx.fillStyle = ctx.strokeStyle = current.transferMapsFallback?.applyToColor(color) ?? color;
    current.fillColor = current.strokeColor = color;
  }
  isModifyingCurrentTransform() {
    return false;
  }
  getPattern(ctx, owner, inverse, pathType, opIdx) {
    const matrix = pathType !== PathType.SHADING ? Util.transform(inverse, this.patternBaseMatrix) : inverse;
    const temporaryPatternCanvas = this.createPatternCanvas(owner, opIdx);
    let domMatrix = new DOMMatrix(matrix);
    domMatrix = domMatrix.translate(temporaryPatternCanvas.offsetX, temporaryPatternCanvas.offsetY);
    domMatrix = domMatrix.scale(1 / temporaryPatternCanvas.scaleX, 1 / temporaryPatternCanvas.scaleY);
    const pattern = ctx.createPattern(temporaryPatternCanvas.canvas, "repeat");
    owner.canvasFactory.destroy(temporaryPatternCanvas.canvasEntry);
    pattern.setTransform(domMatrix);
    return pattern;
  }
}

;// ./src/display/canvas.js






const MIN_FONT_SIZE = 16;
const MAX_FONT_SIZE = 100;
const EXECUTION_TIME = 15;
const EXECUTION_STEPS = 10;
const FULL_CHUNK_HEIGHT = 16;
const XY = new Float32Array(2);
function mirrorContextOperations(ctx, destCtx) {
  if (ctx._removeMirroring) {
    throw new Error("Context is already forwarding operations.");
  }
  const originalMethods = new Map();
  for (const name of ["save", "restore", "rotate", "scale", "translate", "transform", "setTransform", "resetTransform", "clip", "moveTo", "lineTo", "bezierCurveTo", "quadraticCurveTo", "arc", "arcTo", "ellipse", "rect", "roundRect", "closePath", "beginPath"]) {
    const original = ctx[name];
    if (typeof original !== "function" || typeof destCtx[name] !== "function") {
      continue;
    }
    originalMethods.set(name, original);
    ctx[name] = function (...args) {
      destCtx[name](...args);
      return original.apply(this, args);
    };
  }
  ctx._removeMirroring = () => {
    for (const [name, original] of originalMethods) {
      ctx[name] = original;
    }
    delete ctx._removeMirroring;
  };
}
function drawImageAtIntegerCoords(ctx, srcImg, srcX, srcY, srcW, srcH, destX, destY, destW, destH) {
  const [a, b, c, d, tx, ty] = getCurrentTransform(ctx);
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
class CanvasExtraState {
  alphaIsShape = false;
  fontSize = 0;
  fontSizeScale = 1;
  textMatrix = null;
  textMatrixScale = 1;
  fontMatrix = FONT_IDENTITY_MATRIX;
  leading = 0;
  x = 0;
  y = 0;
  lineX = 0;
  lineY = 0;
  charSpacing = 0;
  wordSpacing = 0;
  textHScale = 1;
  textRenderingMode = TextRenderingMode.FILL;
  textRise = 0;
  fillColor = "#000000";
  strokeColor = "#000000";
  tilingPatternDims = null;
  patternFill = false;
  patternStroke = false;
  fillAlpha = 1;
  strokeAlpha = 1;
  lineWidth = 1;
  activeSMask = null;
  transferMaps = "none";
  transferMapsFallback = null;
  minMax = F32_BBOX_INIT.slice();
  constructor(width, height) {
    this.clipBox = new Float32Array([0, 0, width, height]);
  }
  clone() {
    const clone = Object.create(this);
    clone.clipBox = this.clipBox.slice();
    clone.minMax = this.minMax.slice();
    clone.tilingPatternDims = this.tilingPatternDims?.slice();
    return clone;
  }
  getPathBoundingBox(pathType = PathType.FILL, transform = null) {
    const box = this.minMax.slice();
    if (pathType === PathType.STROKE) {
      if (!transform) {
        unreachable("Stroke bounding box must include transform.");
      }
      Util.singularValueDecompose2dScale(transform, XY);
      const xStrokePad = XY[0] * this.lineWidth / 2;
      const yStrokePad = XY[1] * this.lineWidth / 2;
      box[0] -= xStrokePad;
      box[1] -= yStrokePad;
      box[2] += xStrokePad;
      box[3] += yStrokePad;
    }
    return box;
  }
  updateClipFromPath() {
    const intersect = Util.intersect(this.clipBox, this.getPathBoundingBox());
    this.startNewPathAndClipBox(intersect || [0, 0, 0, 0]);
  }
  isEmptyClip() {
    return this.minMax[0] === Infinity;
  }
  startNewPathAndClipBox(box) {
    this.clipBox.set(box, 0);
    this.minMax.set(F32_BBOX_INIT, 0);
  }
  getClippedPathBoundingBox(pathType = PathType.FILL, transform = null) {
    return Util.intersect(this.clipBox, this.getPathBoundingBox(pathType, transform));
  }
}
function putBinaryImageData(ctx, imgData) {
  const {
    width,
    height,
    kind
  } = imgData;
  const partialChunkHeight = height % FULL_CHUNK_HEIGHT;
  const fullChunks = (height - partialChunkHeight) / FULL_CHUNK_HEIGHT;
  const totalChunks = partialChunkHeight === 0 ? fullChunks : fullChunks + 1;
  const chunkImgData = ctx.createImageData(width, FULL_CHUNK_HEIGHT);
  let srcPos = 0;
  const src = imgData.data;
  const dest = chunkImgData.data;
  let i;
  if (kind === ImageKind.GRAYSCALE_1BPP) {
    for (i = 0; i < totalChunks; i++) {
      ({
        srcPos
      } = convertBlackAndWhiteToRGBA({
        src,
        srcPos,
        dest,
        width,
        height: i < fullChunks ? FULL_CHUNK_HEIGHT : partialChunkHeight
      }));
      ctx.putImageData(chunkImgData, 0, i * FULL_CHUNK_HEIGHT);
    }
  } else if (kind === ImageKind.RGBA_32BPP) {
    let j = 0;
    let elemsInThisChunk = width * FULL_CHUNK_HEIGHT * 4;
    for (i = 0; i < fullChunks; i++) {
      dest.set(src.subarray(srcPos, srcPos + elemsInThisChunk));
      srcPos += elemsInThisChunk;
      ctx.putImageData(chunkImgData, 0, j);
      j += FULL_CHUNK_HEIGHT;
    }
    if (i < totalChunks) {
      elemsInThisChunk = width * partialChunkHeight * 4;
      dest.set(src.subarray(srcPos, srcPos + elemsInThisChunk));
      ctx.putImageData(chunkImgData, 0, j);
    }
  } else if (kind === ImageKind.RGB_24BPP) {
    for (i = 0; i < totalChunks; i++) {
      ({
        srcPos
      } = convertRGBToRGBA({
        src,
        srcPos,
        dest: new Uint32Array(dest.buffer),
        width,
        height: i < fullChunks ? FULL_CHUNK_HEIGHT : partialChunkHeight
      }));
      ctx.putImageData(chunkImgData, 0, i * FULL_CHUNK_HEIGHT);
    }
  } else {
    throw new Error(`bad image kind: ${kind}`);
  }
}
function putBinaryImageMask(ctx, imgData) {
  if (imgData.bitmap) {
    ctx.drawImage(imgData.bitmap, 0, 0);
    return;
  }
  const {
    width,
    height
  } = imgData;
  const partialChunkHeight = height % FULL_CHUNK_HEIGHT;
  const fullChunks = (height - partialChunkHeight) / FULL_CHUNK_HEIGHT;
  const totalChunks = partialChunkHeight === 0 ? fullChunks : fullChunks + 1;
  const chunkImgData = ctx.createImageData(width, FULL_CHUNK_HEIGHT);
  let srcPos = 0;
  const src = imgData.data;
  const dest = chunkImgData.data;
  for (let i = 0; i < totalChunks; i++) {
    ({
      srcPos
    } = convertBlackAndWhiteToRGBA({
      src,
      srcPos,
      dest,
      width,
      height: i < fullChunks ? FULL_CHUNK_HEIGHT : partialChunkHeight,
      nonBlackColor: 0
    }));
    ctx.putImageData(chunkImgData, 0, i * FULL_CHUNK_HEIGHT);
  }
}
function copyCtxState(sourceCtx, destCtx) {
  const properties = ["strokeStyle", "fillStyle", "fillRule", "globalAlpha", "lineWidth", "lineCap", "lineJoin", "miterLimit", "globalCompositeOperation", "font", "filter"];
  for (const property of properties) {
    if (sourceCtx[property] !== undefined) {
      destCtx[property] = sourceCtx[property];
    }
  }
  if (sourceCtx.setLineDash !== undefined) {
    destCtx.setLineDash(sourceCtx.getLineDash());
    destCtx.lineDashOffset = sourceCtx.lineDashOffset;
  }
}
function setAnnotationCanvasName(canvas, canvasName) {
  canvas.setAttribute?.("data-canvas-name", canvasName);
  canvas._pdfjsCanvasName = canvasName;
}
function getAnnotationCanvasName(canvas) {
  return canvas._pdfjsCanvasName ?? null;
}
function resetCtxToDefault(ctx) {
  ctx.strokeStyle = ctx.fillStyle = "#000000";
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
  const {
    filter
  } = ctx;
  if (filter !== "none" && filter !== "") {
    ctx.filter = "none";
  }
}
class TransferMapsFallback {
  #maps;
  constructor(maps) {
    const [mapR, mapG = mapR, mapB = mapR] = maps;
    const identityMap = Util.identity0to256Map.slice();
    this.#maps = [mapR || identityMap, mapG || identityMap, mapB || identityMap];
  }
  applyToColor(color) {
    if (typeof color !== "string" || !color.startsWith("#")) {
      return color;
    }
    const [r, g, b] = getRGBA(color);
    const [mapR, mapG, mapB] = this.#maps;
    return Util.makeHexColor(mapR[r], mapG[g], mapB[b]);
  }
  applyToImageData({
    data
  }) {
    const [mapR, mapG, mapB] = this.#maps;
    for (let i = 0, ii = data.length; i < ii; i += 4) {
      data[i] = mapR[data[i]];
      data[i + 1] = mapG[data[i + 1]];
      data[i + 2] = mapB[data[i + 2]];
    }
  }
  applyToCanvas(ctx) {
    const {
      width,
      height
    } = ctx.canvas;
    const imgData = ctx.getImageData(0, 0, width, height);
    this.applyToImageData(imgData);
    ctx.putImageData(imgData, 0, 0);
  }
}
function getImageSmoothingEnabled(transform, interpolate, pixelRatio) {
  if (interpolate) {
    return true;
  }
  Util.singularValueDecompose2dScale(transform, XY);
  const actualScale = Math.fround(pixelRatio * PixelsPerInch.PDF_TO_CSS_UNITS);
  return XY[0] <= actualScale && XY[1] <= actualScale;
}
const LINE_CAP_STYLES = ["butt", "round", "square"];
const LINE_JOIN_STYLES = ["miter", "round", "bevel"];
const NORMAL_CLIP = {};
const EO_CLIP = {};
class CanvasGraphics {
  static #SCALE_MATRIX = null;
  static #pathCaches = new WeakMap();
  #knockoutGroupLevel = 0;
  #knockoutElementDepth = 0;
  #knockoutTempCanvasEntry = null;
  #knockoutSavedCtx = null;
  #knockoutSavedSMaskCtx = null;
  #knockoutSavedGCO = null;
  #knockoutElementAlpha = 1;
  #knockoutFilterCache;
  #knockoutElementGroupMeta = null;
  #groupStackMeta = [];
  constructor(canvasCtx, commonObjs, objs, canvasFactory, filterFactory, {
    optionalContentConfig,
    markedContentStack = null,
    pixelRatio = OutputScale.pixelRatio
  }, annotationCanvasMap, pageColors, dependencyTracker, imagesTracker) {
    this.ctx = canvasCtx;
    this.current = new CanvasExtraState(this.ctx.canvas.width, this.ctx.canvas.height);
    this.stateStack = [];
    this.pendingClip = null;
    this.pendingEOFill = false;
    this.commonObjs = commonObjs;
    this.objs = objs;
    this.canvasFactory = canvasFactory;
    this.filterFactory = filterFactory;
    this.groupStack = [];
    this.baseTransform = null;
    this.baseTransformStack = [];
    this.groupLevel = 0;
    this.smaskStack = [];
    this.tempSMask = null;
    this.smaskGroupCanvases = [];
    this.smaskPreparedEntry = null;
    this.smaskPreparedFor = null;
    this.smaskPreparedOffsetX = 0;
    this.smaskPreparedOffsetY = 0;
    this.smaskPreparedOOBAlpha = null;
    this.suspendedCtx = null;
    this.contentVisible = true;
    this.markedContentStack = markedContentStack || [];
    this.optionalContentConfig = optionalContentConfig;
    this.pixelRatio = pixelRatio;
    this.cachedPatterns = new Map();
    this.annotationCanvasMap = annotationCanvasMap;
    this.viewportScale = 1;
    this.outputScaleX = 1;
    this.outputScaleY = 1;
    this.pageColors = pageColors;
    this._cachedScaleForStroking = [-1, 0];
    this._cachedBitmapsMap = new Map();
    this.dependencyTracker = dependencyTracker ?? null;
    this.imagesTracker = imagesTracker ?? null;
  }
  getObject(opIdx, data, fallback = null) {
    if (typeof data === "string") {
      this.dependencyTracker?.recordNamedDependency(opIdx, data);
      return data.startsWith("g_") ? this.commonObjs.get(data) : this.objs.get(data);
    }
    return fallback;
  }
  beginDrawing({
    transform,
    viewport,
    transparency = false,
    background = null
  }) {
    const width = this.ctx.canvas.width;
    const height = this.ctx.canvas.height;
    const savedFillStyle = this.ctx.fillStyle;
    this.ctx.fillStyle = background || "#ffffff";
    this.ctx.fillRect(0, 0, width, height);
    this.ctx.fillStyle = savedFillStyle;
    if (transparency) {
      const transparentCanvas = this.transparentCanvasEntry = this.canvasFactory.create(width, height);
      this.compositeCtx = this.ctx;
      ({
        canvas: this.transparentCanvas,
        context: this.ctx
      } = transparentCanvas);
      this.ctx.save();
      this.ctx.transform(...getCurrentTransform(this.compositeCtx));
    }
    this.ctx.save();
    resetCtxToDefault(this.ctx);
    if (transform) {
      this.ctx.transform(...transform);
      this.outputScaleX = transform[0];
      this.outputScaleY = transform[3];
    }
    this.ctx.transform(...viewport.transform);
    this.viewportScale = viewport.scale;
    this.baseTransform = getCurrentTransform(this.ctx);
  }
  executeOperatorList(operatorList, executionStartIdx, continueCallback, errorCallback, stepper, operationsFilter) {
    const argsArray = operatorList.argsArray;
    const fnArray = operatorList.fnArray;
    const prevPathCache = this._pathCache;
    this._pathCache = operatorList.pathCache ?? CanvasGraphics.#pathCaches.getOrInsertComputed(operatorList, makeMap);
    try {
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
      let fnId, fnArgs;
      while (true) {
        if (stepper !== undefined) {
          if (i === stepper.nextBreakPoint) {
            stepper.breakIt(i, continueCallback);
            return i;
          }
          if (stepper.shouldSkip(i)) {
            if (++i === argsArrayLen) {
              return i;
            }
            continue;
          }
        }
        if (!operationsFilter || operationsFilter(i, operatorList)) {
          fnId = fnArray[i];
          fnArgs = argsArray[i] ?? null;
          if (fnId !== OPS.dependency) {
            if (fnArgs === null) {
              this[fnId](i);
            } else {
              this[fnId](i, ...fnArgs);
            }
          } else {
            for (const depObjId of fnArgs) {
              this.dependencyTracker?.recordNamedData(depObjId, i);
              const objsPool = depObjId.startsWith("g_") ? commonObjs : objs;
              if (!objsPool.has(depObjId)) {
                objsPool.get(depObjId, continueCallback, errorCallback);
                return i;
              }
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
    } finally {
      this._pathCache = prevPathCache;
    }
  }
  #restoreInitialState() {
    while (this.stateStack.length || this.inSMaskMode) {
      this.restore();
    }
    this.current.activeSMask = null;
    this.ctx.restore();
    if (this.transparentCanvas) {
      this.ctx = this.compositeCtx;
      this.ctx.save();
      this.ctx.setTransform(1, 0, 0, 1, 0, 0);
      this.ctx.drawImage(this.transparentCanvas, 0, 0);
      this.ctx.restore();
      this.canvasFactory.destroy(this.transparentCanvasEntry);
      this.transparentCanvas = null;
      this.transparentCanvasEntry = null;
    }
  }
  endDrawing() {
    this.#restoreInitialState();
    for (const canvas of this.smaskGroupCanvases) {
      this.canvasFactory.destroy(canvas);
    }
    this.smaskGroupCanvases.length = 0;
    this._clearPreparedSMask();
    this.tempSMask = null;
    this.smaskStack.length = 0;
    for (const meta of this.#groupStackMeta) {
      this.#destroyKnockoutPools(meta);
    }
    this.#groupStackMeta.length = 0;
    this.#knockoutTempCanvasEntry = null;
    this.#knockoutSavedCtx = null;
    this.#knockoutSavedSMaskCtx = null;
    this.#knockoutSavedGCO = null;
    this.#knockoutElementAlpha = 1;
    this.#knockoutElementGroupMeta = null;
    this.#knockoutElementDepth = 0;
    this.#knockoutGroupLevel = 0;
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
    this.#drawFilter();
  }
  #drawFilter() {
    if (this.pageColors) {
      const hcmFilterId = this.filterFactory.addHCMFilter(this.pageColors.foreground, this.pageColors.background);
      if (hcmFilterId !== "none") {
        const savedFilter = this.ctx.filter;
        this.ctx.filter = hcmFilterId;
        this.ctx.drawImage(this.ctx.canvas, 0, 0);
        this.ctx.filter = savedFilter;
      }
    }
  }
  _scaleImage(img, inverseTransform) {
    const width = img.width ?? img.displayWidth;
    const height = img.height ?? img.displayHeight;
    const widthScale = Math.max(Math.hypot(inverseTransform[0], inverseTransform[1]), 1);
    const heightScale = Math.max(Math.hypot(inverseTransform[2], inverseTransform[3]), 1);
    const scaleSteps = [];
    let ws = widthScale,
      hs = heightScale,
      pw = width,
      ph = height;
    while (ws > 2 && pw > 1 || hs > 2 && ph > 1) {
      let nw = pw,
        nh = ph;
      if (ws > 2 && pw > 1) {
        nw = Math.ceil(pw / 2);
        ws /= pw / nw;
      }
      if (hs > 2 && ph > 1) {
        nh = Math.ceil(ph / 2);
        hs /= ph / nh;
      }
      scaleSteps.push({
        newWidth: nw,
        newHeight: nh
      });
      pw = nw;
      ph = nh;
    }
    if (scaleSteps.length === 0) {
      return {
        img,
        paintWidth: width,
        paintHeight: height,
        tmpCanvas: null
      };
    }
    if (scaleSteps.length === 1) {
      const {
        newWidth,
        newHeight
      } = scaleSteps[0];
      const tmpCanvas = this.canvasFactory.create(newWidth, newHeight);
      tmpCanvas.context.drawImage(img, 0, 0, width, height, 0, 0, newWidth, newHeight);
      return {
        img: tmpCanvas.canvas,
        paintWidth: newWidth,
        paintHeight: newHeight,
        tmpCanvas
      };
    }
    let readEntry = this.canvasFactory.create(1, 1);
    let writeEntry = this.canvasFactory.create(1, 1);
    let paintWidth = width,
      paintHeight = height;
    let source = img;
    for (const {
      newWidth,
      newHeight
    } of scaleSteps) {
      this.canvasFactory.reset(writeEntry, newWidth, newHeight);
      writeEntry.context.drawImage(source, 0, 0, paintWidth, paintHeight, 0, 0, newWidth, newHeight);
      [readEntry, writeEntry] = [writeEntry, readEntry];
      source = readEntry.canvas;
      paintWidth = newWidth;
      paintHeight = newHeight;
    }
    this.canvasFactory.destroy(writeEntry);
    return {
      img: readEntry.canvas,
      paintWidth,
      paintHeight,
      tmpCanvas: readEntry
    };
  }
  _createMaskCanvas(opIdx, img) {
    const ctx = this.ctx;
    const {
      width,
      height
    } = img;
    const isPatternFill = this.current.patternFill;
    const fillColor = isPatternFill ? this.current.fillColor : ctx.fillStyle;
    const currentTransform = getCurrentTransform(ctx);
    let cache, cacheKey, scaled, maskCanvas;
    if ((img.bitmap || img.data) && img.count > 1) {
      const mainKey = img.bitmap || img.data.buffer;
      cacheKey = JSON.stringify(isPatternFill ? currentTransform : [currentTransform.slice(0, 4), fillColor]);
      cache = this._cachedBitmapsMap.getOrInsertComputed(mainKey, makeMap);
      const cachedImage = cache.get(cacheKey);
      if (cachedImage && !isPatternFill) {
        const offsetX = Math.round(Math.min(currentTransform[0], currentTransform[2]) + currentTransform[4]);
        const offsetY = Math.round(Math.min(currentTransform[1], currentTransform[3]) + currentTransform[5]);
        this.dependencyTracker?.recordDependencies(opIdx, Dependencies.transformAndFill);
        return {
          canvas: cachedImage,
          offsetX,
          offsetY
        };
      }
      scaled = cachedImage;
    }
    if (!scaled) {
      maskCanvas = this.canvasFactory.create(width, height);
      putBinaryImageMask(maskCanvas.context, img);
    }
    let maskToCanvas = Util.transform(currentTransform, [1 / width, 0, 0, -1 / height, 0, 0]);
    maskToCanvas = Util.transform(maskToCanvas, [1, 0, 0, 1, 0, -height]);
    const minMax = F32_BBOX_INIT.slice();
    Util.axialAlignedBoundingBox([0, 0, width, height], maskToCanvas, minMax);
    const [minX, minY, maxX, maxY] = minMax;
    const drawnWidth = Math.round(maxX - minX) || 1;
    const drawnHeight = Math.round(maxY - minY) || 1;
    const fillCanvas = this.canvasFactory.create(drawnWidth, drawnHeight);
    const fillCtx = fillCanvas.context;
    const offsetX = minX;
    const offsetY = minY;
    fillCtx.translate(-offsetX, -offsetY);
    fillCtx.transform(...maskToCanvas);
    let scaledEntry = null;
    if (!scaled) {
      const scaleResult = this._scaleImage(maskCanvas.canvas, getCurrentTransformInverse(fillCtx));
      scaled = scaleResult.img;
      scaledEntry = scaleResult.tmpCanvas;
      if (scaled !== maskCanvas.canvas) {
        this.canvasFactory.destroy(maskCanvas);
        maskCanvas = null;
      }
      if (cache && isPatternFill) {
        cache.set(cacheKey, scaled);
        scaledEntry = null;
        maskCanvas = null;
      }
    }
    fillCtx.imageSmoothingEnabled = getImageSmoothingEnabled(getCurrentTransform(fillCtx), img.interpolate, this.pixelRatio);
    drawImageAtIntegerCoords(fillCtx, scaled, 0, 0, scaled.width, scaled.height, 0, 0, width, height);
    if (scaledEntry) {
      this.canvasFactory.destroy(scaledEntry);
    }
    if (maskCanvas) {
      this.canvasFactory.destroy(maskCanvas);
    }
    fillCtx.globalCompositeOperation = "source-in";
    const inverse = Util.transform(getCurrentTransformInverse(fillCtx), [1, 0, 0, 1, -offsetX, -offsetY]);
    fillCtx.fillStyle = isPatternFill ? fillColor.getPattern(ctx, this, inverse, PathType.FILL, opIdx) : fillColor;
    fillCtx.fillRect(0, 0, width, height);
    if (cache && !isPatternFill) {
      cache.set(cacheKey, fillCanvas.canvas);
    }
    this.dependencyTracker?.recordDependencies(opIdx, Dependencies.transformAndFill);
    return {
      canvas: fillCanvas.canvas,
      canvasEntry: cache && !isPatternFill ? null : fillCanvas,
      offsetX: Math.round(offsetX),
      offsetY: Math.round(offsetY)
    };
  }
  setLineWidth(opIdx, width) {
    this.dependencyTracker?.recordSimpleData("lineWidth", opIdx);
    if (width !== this.current.lineWidth) {
      this._cachedScaleForStroking[0] = -1;
    }
    this.current.lineWidth = width;
    this.ctx.lineWidth = width;
  }
  setLineCap(opIdx, style) {
    this.dependencyTracker?.recordSimpleData("lineCap", opIdx);
    this.ctx.lineCap = LINE_CAP_STYLES[style];
  }
  setLineJoin(opIdx, style) {
    this.dependencyTracker?.recordSimpleData("lineJoin", opIdx);
    this.ctx.lineJoin = LINE_JOIN_STYLES[style];
  }
  setMiterLimit(opIdx, limit) {
    this.dependencyTracker?.recordSimpleData("miterLimit", opIdx);
    this.ctx.miterLimit = limit;
  }
  setDash(opIdx, dashArray, dashPhase) {
    this.dependencyTracker?.recordSimpleData("dash", opIdx);
    const ctx = this.ctx;
    if (ctx.setLineDash !== undefined) {
      ctx.setLineDash(dashArray);
      ctx.lineDashOffset = dashPhase;
    }
  }
  setRenderingIntent(opIdx, intent) {}
  setFlatness(opIdx, flatness) {}
  setGState(opIdx, states) {
    for (const [key, value] of states) {
      switch (key) {
        case "LW":
          this.setLineWidth(opIdx, value);
          break;
        case "LC":
          this.setLineCap(opIdx, value);
          break;
        case "LJ":
          this.setLineJoin(opIdx, value);
          break;
        case "ML":
          this.setMiterLimit(opIdx, value);
          break;
        case "D":
          this.setDash(opIdx, value[0], value[1]);
          break;
        case "RI":
          this.setRenderingIntent(opIdx, value);
          break;
        case "FL":
          this.setFlatness(opIdx, value);
          break;
        case "Font":
          this.setFont(opIdx, value[0], value[1]);
          break;
        case "CA":
          this.dependencyTracker?.recordSimpleData("strokeAlpha", opIdx);
          this.current.strokeAlpha = value;
          break;
        case "ca":
          this.dependencyTracker?.recordSimpleData("fillAlpha", opIdx);
          this.ctx.globalAlpha = this.current.fillAlpha = value;
          break;
        case "BM":
          this.dependencyTracker?.recordSimpleData("globalCompositeOperation", opIdx);
          this.ctx.globalCompositeOperation = value;
          break;
        case "SMask":
          this.dependencyTracker?.recordSimpleData("SMask", opIdx);
          this.current.activeSMask = value ? this.tempSMask : null;
          if (this.current.activeSMask) {
            this.current.activeSMask.blendMode = this.ctx.globalCompositeOperation;
          }
          this.tempSMask = null;
          this.checkSMaskState(opIdx);
          break;
        case "TR":
          {
            this.dependencyTracker?.recordSimpleData("filter", opIdx);
            let filter = this.filterFactory.addFilter(value);
            this.ctx.filter = filter;
            let fallback = null;
            if (value && (filter === "none" || !FeatureTest.isCanvasFilterSupported || this.ctx.filter === "none" || this.ctx.filter === "")) {
              this.ctx.filter = filter = "none";
              fallback = new TransferMapsFallback(value);
            }
            this.current.transferMaps = filter;
            if (fallback || this.current.transferMapsFallback) {
              this.current.transferMapsFallback = fallback;
              if (!this.current.patternFill) {
                this.ctx.fillStyle = this.#transferColor(this.current.fillColor);
              }
              if (!this.current.patternStroke) {
                this.ctx.strokeStyle = this.#transferColor(this.current.strokeColor);
              }
            }
            break;
          }
      }
    }
  }
  get inSMaskMode() {
    return !!this.suspendedCtx;
  }
  _clearPreparedSMask() {
    if (this.smaskPreparedEntry) {
      this.canvasFactory.destroy(this.smaskPreparedEntry);
      this.smaskPreparedEntry = null;
    }
    this.smaskPreparedFor = null;
    this.smaskPreparedOffsetX = 0;
    this.smaskPreparedOffsetY = 0;
    this.smaskPreparedOOBAlpha = null;
  }
  _ensurePreparedSMask(smask) {
    if (smask === this.smaskPreparedFor) {
      return;
    }
    this._clearPreparedSMask();
    this._prepareSMaskCanvas(smask);
  }
  checkSMaskState(opIdx) {
    const inSMaskMode = this.inSMaskMode;
    if (this.current.activeSMask && !inSMaskMode) {
      this.beginSMaskMode(opIdx);
    } else if (!this.current.activeSMask && inSMaskMode) {
      this.endSMaskMode();
    } else if (this.current.activeSMask && inSMaskMode) {
      this._ensurePreparedSMask(this.current.activeSMask);
    }
  }
  _prepareSMaskCanvas(smask) {
    const {
      canvas: maskCanvas,
      subtype,
      backdrop,
      transferMap
    } = smask;
    const hasFilter = subtype === "Luminosity" || subtype === "Alpha" && transferMap;
    if (!hasFilter && !(subtype === "Luminosity" && backdrop)) {
      this.smaskPreparedFor = smask;
      return;
    }
    let filteredOOBAlpha;
    if (subtype === "Luminosity" && backdrop) {
      const [r, g, b] = getRGBA(backdrop);
      const inputAlpha = Math.round(0.3 * r + 0.59 * g + 0.11 * b);
      filteredOOBAlpha = transferMap?.[inputAlpha] ?? inputAlpha;
    } else {
      filteredOOBAlpha = transferMap?.[0] ?? 0;
    }
    const SMASK_LAYER_TO_MASK_AREA_RATIO = 4;
    const {
      width: layerW,
      height: layerH
    } = this.ctx.canvas;
    const maskArea = maskCanvas.width * maskCanvas.height;
    const useLayerSize = layerW * layerH < SMASK_LAYER_TO_MASK_AREA_RATIO * maskArea;
    const filterSpec = hasFilter ? {
      url: subtype === "Alpha" ? this.filterFactory.addAlphaFilter(transferMap) : this.filterFactory.addLuminosityFilter(transferMap),
      subtype,
      transferMap
    } : null;
    const bakedBackdrop = subtype === "Luminosity" ? backdrop : null;
    let preparedEntry, offsetX, offsetY;
    if (useLayerSize) {
      preparedEntry = this._bakeSMaskCanvas(maskCanvas, smask.offsetX, smask.offsetY, layerW, layerH, bakedBackdrop, filterSpec);
      offsetX = 0;
      offsetY = 0;
    } else {
      preparedEntry = this._bakeSMaskCanvas(maskCanvas, 0, 0, maskCanvas.width, maskCanvas.height, bakedBackdrop, filterSpec);
      offsetX = smask.offsetX;
      offsetY = smask.offsetY;
    }
    this.smaskPreparedEntry = preparedEntry;
    this.smaskPreparedFor = smask;
    this.smaskPreparedOffsetX = offsetX;
    this.smaskPreparedOffsetY = offsetY;
    this.smaskPreparedOOBAlpha = !useLayerSize && filteredOOBAlpha !== 0 ? filteredOOBAlpha : null;
  }
  _bakeSMaskCanvas(maskCanvas, drawX, drawY, w, h, backdrop, filterSpec) {
    if (!backdrop && !filterSpec) {
      unreachable("_bakeSMaskCanvas with neither backdrop nor filter");
    }
    const srcEntry = this.canvasFactory.create(w, h);
    const sCtx = srcEntry.context;
    sCtx.drawImage(maskCanvas, drawX, drawY);
    if (backdrop) {
      sCtx.globalCompositeOperation = "destination-atop";
      sCtx.fillStyle = backdrop;
      sCtx.fillRect(0, 0, w, h);
    }
    if (!filterSpec) {
      return srcEntry;
    }
    const preparedEntry = this.canvasFactory.create(w, h);
    const pCtx = preparedEntry.context;
    pCtx.filter = filterSpec.url;
    const filterApplied = FeatureTest.isCanvasFilterSupported && pCtx.filter !== "none" && pCtx.filter !== "";
    pCtx.drawImage(srcEntry.canvas, 0, 0);
    if (FeatureTest.isCanvasFilterSupported) {
      pCtx.filter = "none";
    }
    if (!filterApplied) {
      const img = pCtx.getImageData(0, 0, w, h);
      const {
        data
      } = img;
      const {
        transferMap
      } = filterSpec;
      if (filterSpec.subtype === "Luminosity") {
        for (let i = 0, ii = data.length; i < ii; i += 4) {
          const a = 0.3 * data[i] + 0.59 * data[i + 1] + 0.11 * data[i + 2] + 0.5 | 0;
          data[i] = data[i + 1] = data[i + 2] = 0;
          data[i + 3] = transferMap?.[a] ?? a;
        }
      } else {
        for (let i = 3, ii = data.length; i < ii; i += 4) {
          data[i] = transferMap[data[i]];
        }
      }
      pCtx.putImageData(img, 0, 0);
    }
    this.canvasFactory.destroy(srcEntry);
    return preparedEntry;
  }
  beginSMaskMode(opIdx) {
    if (this.inSMaskMode) {
      throw new Error("beginSMaskMode called while already in smask mode");
    }
    const {
      width: drawnWidth,
      height: drawnHeight
    } = this.ctx.canvas;
    const scratchCanvas = this.canvasFactory.create(drawnWidth, drawnHeight);
    this.smaskScratchCanvas = scratchCanvas;
    this.suspendedCtx = this.ctx;
    const ctx = this.ctx = scratchCanvas.context;
    ctx.setTransform(this.suspendedCtx.getTransform());
    copyCtxState(this.suspendedCtx, ctx);
    mirrorContextOperations(ctx, this.suspendedCtx);
    this._ensurePreparedSMask(this.current.activeSMask);
    this.setGState(opIdx, [["BM", "source-over"]]);
  }
  endSMaskMode() {
    if (!this.inSMaskMode) {
      throw new Error("endSMaskMode called while not in smask mode");
    }
    this.ctx._removeMirroring();
    copyCtxState(this.ctx, this.suspendedCtx);
    this.ctx = this.suspendedCtx;
    this.suspendedCtx = null;
    this.canvasFactory.destroy(this.smaskScratchCanvas);
    this.smaskScratchCanvas = null;
    this._clearPreparedSMask();
  }
  #createKnockoutMaskCanvas(sourceCanvas, reuseEntry = null, alpha = 1) {
    const {
      width,
      height
    } = sourceCanvas;
    const maskEntry = reuseEntry ?? this.canvasFactory.create(width, height);
    const maskCtx = maskEntry.context;
    alpha = Math.round(alpha * 255) / 255;
    const needsAlphaScaling = alpha < 1;
    if (needsAlphaScaling && this.#knockoutFilterCache === undefined) {
      this.#knockoutFilterCache = FeatureTest.isCanvasFilterSupported ? new Map() : "none";
    }
    let knockoutFilter = "none";
    if (needsAlphaScaling && this.#knockoutFilterCache instanceof Map) {
      knockoutFilter = this.#knockoutFilterCache.getOrInsertComputed(alpha, () => this.filterFactory.addKnockoutFilter(alpha));
    }
    if (!needsAlphaScaling || knockoutFilter !== "none") {
      if (reuseEntry) {
        maskCtx.save();
        maskCtx.setTransform(1, 0, 0, 1, 0, 0);
        maskCtx.clearRect(0, 0, width, height);
        maskCtx.restore();
      }
      maskCtx.filter = knockoutFilter;
      maskCtx.drawImage(sourceCanvas, 0, 0);
      maskCtx.filter = "none";
      return maskEntry;
    }
    const sourceData = sourceCanvas.getContext("2d", {
      willReadFrequently: true
    }).getImageData(0, 0, width, height);
    const maskData = maskCtx.createImageData(width, height);
    const sourcePixels = sourceData.data,
      maskPixels = maskData.data;
    const alphaScale = alpha > 0 ? 1 / alpha : 1e6;
    for (let i = 3, ii = sourcePixels.length; i < ii; i += 4) {
      maskPixels[i] = Math.min(Math.round(sourcePixels[i] * alphaScale), 255);
    }
    maskCtx.putImageData(maskData, 0, 0);
    return maskEntry;
  }
  #getOrCreatePooledEntry(meta, key, width, height) {
    let entry = meta?.[key] ?? null;
    if (entry && (entry.canvas.width !== width || entry.canvas.height !== height)) {
      this.canvasFactory.destroy(entry);
      entry = null;
    }
    if (!entry) {
      entry = this.canvasFactory.create(width, height);
      if (meta) {
        meta[key] = entry;
      }
      return entry;
    }
    const ctx = entry.context;
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.clearRect(0, 0, width, height);
    ctx.restore();
    return entry;
  }
  #compositeKnockoutSurface(destCtx, surfaceCanvas, options = {}) {
    const {
      backdropCanvas = null,
      destTransform = [1, 0, 0, 1, 0, 0],
      backdropOffset = [0, 0],
      reuseMaskEntry = null,
      poolMeta = null,
      sourceAlpha = 1,
      sourceFilter = "none",
      knockoutAlpha = 1
    } = options;
    const {
      width,
      height
    } = surfaceCanvas;
    const knockoutMaskEntry = this.#createKnockoutMaskCanvas(surfaceCanvas, reuseMaskEntry, knockoutAlpha);
    const sourceCompositeOperation = destCtx.globalCompositeOperation;
    destCtx.save();
    destCtx.setTransform(...destTransform);
    destCtx.globalAlpha = 1;
    if (FeatureTest.isCanvasFilterSupported) {
      destCtx.filter = "none";
    }
    destCtx.globalCompositeOperation = "destination-out";
    destCtx.drawImage(knockoutMaskEntry.canvas, 0, 0);
    if (backdropCanvas) {
      const [bx, by] = backdropOffset;
      const backdropEntry = this.#getOrCreatePooledEntry(poolMeta, "knockoutBackdropEntry", width, height);
      const backdropCtx = backdropEntry.context;
      backdropCtx.drawImage(backdropCanvas, bx, by, width, height, 0, 0, width, height);
      backdropCtx.globalCompositeOperation = "destination-in";
      backdropCtx.drawImage(knockoutMaskEntry.canvas, 0, 0);
      backdropCtx.globalCompositeOperation = "source-over";
      destCtx.globalCompositeOperation = "destination-over";
      destCtx.drawImage(backdropEntry.canvas, 0, 0);
      if (!poolMeta) {
        this.canvasFactory.destroy(backdropEntry);
      }
    }
    destCtx.globalCompositeOperation = sourceCompositeOperation;
    destCtx.globalAlpha = sourceAlpha;
    if (FeatureTest.isCanvasFilterSupported) {
      destCtx.filter = sourceFilter ?? "none";
    }
    destCtx.drawImage(surfaceCanvas, 0, 0);
    destCtx.restore();
    if (!reuseMaskEntry) {
      this.canvasFactory.destroy(knockoutMaskEntry);
    }
  }
  #beginKnockoutElement(alpha = 1) {
    if (this.#knockoutGroupLevel === 0 || this.#knockoutElementDepth > 0 || !this.contentVisible) {
      return false;
    }
    this.#knockoutElementDepth++;
    this.#knockoutElementAlpha = alpha;
    const groupMeta = this.#groupStackMeta.at(-1);
    const {
      canvas
    } = this.ctx;
    const tempEntry = this.#getOrCreatePooledEntry(groupMeta, "knockoutTempEntry", canvas.width, canvas.height);
    this.#knockoutTempCanvasEntry = tempEntry;
    const tempCtx = tempEntry.context;
    tempCtx.save();
    tempCtx.setTransform(this.ctx.getTransform());
    copyCtxState(this.ctx, tempCtx);
    this.#knockoutSavedGCO = tempCtx.globalCompositeOperation;
    tempCtx.globalCompositeOperation = "source-over";
    mirrorContextOperations(tempCtx, this.ctx);
    this.#knockoutElementGroupMeta = groupMeta;
    this.#knockoutSavedCtx = this.ctx;
    this.#knockoutSavedSMaskCtx = this.suspendedCtx;
    this.ctx = tempCtx;
    if (this.inSMaskMode) {
      this.suspendedCtx = tempCtx;
    }
    return true;
  }
  #endKnockoutElement(started) {
    if (!started) {
      return;
    }
    const tempEntry = this.#knockoutTempCanvasEntry;
    const savedCtx = this.#knockoutSavedCtx;
    const savedSMaskCtx = this.#knockoutSavedSMaskCtx;
    const tempCtx = tempEntry.context;
    this.#knockoutTempCanvasEntry = null;
    this.#knockoutSavedCtx = null;
    this.#knockoutSavedSMaskCtx = null;
    if (this.inSMaskMode && this.suspendedCtx === tempCtx && this.ctx !== tempCtx) {
      this.endSMaskMode();
    }
    if (this.inSMaskMode) {
      this.suspendedCtx = savedSMaskCtx;
    }
    this.ctx._removeMirroring();
    this.ctx.globalCompositeOperation = this.#knockoutSavedGCO;
    this.#knockoutSavedGCO = null;
    copyCtxState(this.ctx, savedCtx);
    this.ctx = savedCtx;
    const groupMeta = this.#knockoutElementGroupMeta;
    this.#knockoutElementGroupMeta = null;
    const knockoutAlpha = this.#knockoutElementAlpha;
    this.#knockoutElementAlpha = 1;
    try {
      this.#compositeKnockoutSurface(savedSMaskCtx ?? savedCtx, tempEntry.canvas, {
        backdropCanvas: groupMeta?.backdropCtx?.canvas ?? null,
        backdropOffset: groupMeta?.backdropCtx ? [groupMeta.offsetX, groupMeta.offsetY] : [0, 0],
        reuseMaskEntry: groupMeta?.knockoutMaskEntry ?? null,
        poolMeta: groupMeta,
        knockoutAlpha
      });
    } finally {
      tempCtx.restore();
      this.#knockoutElementDepth--;
      if (!groupMeta) {
        this.canvasFactory.destroy(tempEntry);
      }
    }
  }
  compose(dirtyBox) {
    if (!this.current.activeSMask) {
      return;
    }
    dirtyBox = dirtyBox ? [Math.floor(dirtyBox[0]), Math.floor(dirtyBox[1]), Math.ceil(dirtyBox[2]), Math.ceil(dirtyBox[3])] : [0, 0, this.ctx.canvas.width, this.ctx.canvas.height];
    const smask = this.current.activeSMask;
    const suspendedCtx = this.suspendedCtx;
    const applySMaskInPlace = this.#knockoutElementDepth > 0 && suspendedCtx === this.ctx;
    this.composeSMask(applySMaskInPlace ? null : suspendedCtx, smask, this.ctx, dirtyBox);
    if (applySMaskInPlace) {
      return;
    }
    this.ctx.save();
    this.ctx.setTransform(1, 0, 0, 1, 0, 0);
    this.ctx.clearRect(0, 0, this.ctx.canvas.width, this.ctx.canvas.height);
    this.ctx.restore();
  }
  composeSMask(ctx, smask, layerCtx, layerBox) {
    const layerOffsetX = layerBox[0];
    const layerOffsetY = layerBox[1];
    const layerWidth = layerBox[2] - layerOffsetX;
    const layerHeight = layerBox[3] - layerOffsetY;
    if (layerWidth === 0 || layerHeight === 0) {
      return;
    }
    const preparedEntry = this.smaskPreparedEntry;
    if (preparedEntry) {
      let clipX = layerOffsetX;
      let clipY = layerOffsetY;
      let clipW = layerWidth;
      let clipH = layerHeight;
      const oobAlpha = this.smaskPreparedOOBAlpha;
      const hasOOBAlpha = oobAlpha !== null;
      if (hasOOBAlpha) {
        clipX = Math.max(layerOffsetX, smask.offsetX);
        clipY = Math.max(layerOffsetY, smask.offsetY);
        const x1 = Math.min(layerOffsetX + layerWidth, smask.offsetX + smask.canvas.width);
        const y1 = Math.min(layerOffsetY + layerHeight, smask.offsetY + smask.canvas.height);
        clipW = x1 - clipX;
        clipH = y1 - clipY;
      }
      if (clipW > 0 && clipH > 0) {
        const srcX = clipX - this.smaskPreparedOffsetX;
        const srcY = clipY - this.smaskPreparedOffsetY;
        layerCtx.save();
        layerCtx.globalAlpha = 1;
        layerCtx.setTransform(1, 0, 0, 1, 0, 0);
        const clip = new Path2D();
        clip.rect(clipX, clipY, clipW, clipH);
        layerCtx.clip(clip);
        layerCtx.globalCompositeOperation = "destination-in";
        layerCtx.drawImage(preparedEntry.canvas, srcX, srcY, clipW, clipH, clipX, clipY, clipW, clipH);
        layerCtx.restore();
      }
      if (hasOOBAlpha && oobAlpha < 255) {
        this._applySMaskOOBAlpha(layerCtx, layerOffsetX, layerOffsetY, layerWidth, layerHeight, clipX, clipY, clipX + clipW, clipY + clipH, oobAlpha);
      }
    } else {
      this.genericComposeSMask(smask, layerCtx, layerWidth, layerHeight, layerOffsetX, layerOffsetY);
    }
    if (!ctx) {
      return;
    }
    ctx.save();
    ctx.globalAlpha = 1;
    ctx.globalCompositeOperation = smask.blendMode || "source-over";
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.drawImage(layerCtx.canvas, layerOffsetX, layerOffsetY, layerWidth, layerHeight, layerOffsetX, layerOffsetY, layerWidth, layerHeight);
    ctx.restore();
  }
  _applySMaskOOBAlpha(layerCtx, layerOffsetX, layerOffsetY, layerWidth, layerHeight, maskX0, maskY0, maskX1, maskY1, alpha) {
    const hasInnerCutout = maskX0 < maskX1 && maskY0 < maskY1;
    if (hasInnerCutout && maskX0 === layerOffsetX && maskY0 === layerOffsetY && maskX1 === layerOffsetX + layerWidth && maskY1 === layerOffsetY + layerHeight) {
      return;
    }
    const path = new Path2D();
    path.rect(layerOffsetX, layerOffsetY, layerWidth, layerHeight);
    if (hasInnerCutout) {
      path.rect(maskX0, maskY0, maskX1 - maskX0, maskY1 - maskY0);
    }
    layerCtx.save();
    layerCtx.globalAlpha = alpha / 255;
    layerCtx.setTransform(1, 0, 0, 1, 0, 0);
    layerCtx.clip(path, "evenodd");
    layerCtx.globalCompositeOperation = "destination-in";
    layerCtx.fillStyle = "#000000";
    layerCtx.fillRect(layerOffsetX, layerOffsetY, layerWidth, layerHeight);
    layerCtx.restore();
  }
  genericComposeSMask(smask, layerCtx, width, height, layerOffsetX, layerOffsetY) {
    const {
      context: maskCtx,
      offsetX: maskOffsetX,
      offsetY: maskOffsetY
    } = smask;
    layerCtx.save();
    layerCtx.globalAlpha = 1;
    layerCtx.setTransform(1, 0, 0, 1, 0, 0);
    const clip = new Path2D();
    clip.rect(layerOffsetX, layerOffsetY, width, height);
    layerCtx.clip(clip);
    layerCtx.globalCompositeOperation = "destination-in";
    layerCtx.drawImage(maskCtx.canvas, layerOffsetX - maskOffsetX, layerOffsetY - maskOffsetY, width, height, layerOffsetX, layerOffsetY, width, height);
    layerCtx.restore();
  }
  save(opIdx) {
    if (this.inSMaskMode) {
      copyCtxState(this.ctx, this.suspendedCtx);
    }
    this.ctx.save();
    const old = this.current;
    this.stateStack.push(old);
    this.current = old.clone();
    this.dependencyTracker?.save(opIdx);
  }
  restore(opIdx) {
    this.dependencyTracker?.restore(opIdx);
    if (this.stateStack.length === 0) {
      if (this.inSMaskMode) {
        this.endSMaskMode();
      }
      return;
    }
    this.current = this.stateStack.pop();
    this.ctx.restore();
    if (this.inSMaskMode) {
      copyCtxState(this.suspendedCtx, this.ctx);
      this.ctx.setTransform(this.suspendedCtx.getTransform());
    }
    this.checkSMaskState(opIdx);
    this.pendingClip = null;
    this._cachedScaleForStroking[0] = -1;
  }
  resetGraphicsState() {
    const {
      clipBox,
      transferMaps,
      transferMapsFallback
    } = this.current;
    const current = this.current = new CanvasExtraState(0, 0);
    current.clipBox = clipBox;
    current.transferMaps = transferMaps;
    current.transferMapsFallback = transferMapsFallback;
    const ctx = this.ctx;
    ctx.lineWidth = 1;
    ctx.lineCap = "butt";
    ctx.lineJoin = "miter";
    ctx.miterLimit = 10;
    if (ctx.setLineDash !== undefined) {
      ctx.setLineDash([]);
      ctx.lineDashOffset = 0;
    }
    this._cachedScaleForStroking[0] = -1;
  }
  transform(opIdx, a, b, c, d, e, f) {
    this.dependencyTracker?.recordIncrementalData("transform", opIdx);
    this.ctx.transform(a, b, c, d, e, f);
    this._cachedScaleForStroking[0] = -1;
  }
  constructPath(opIdx, op, data, minMax) {
    let path = this._pathCache.get(opIdx);
    if (!minMax) {
      if (!path) {
        path = new Path2D();
        this._pathCache.set(opIdx, path);
      }
      if (op !== OPS.stroke && op !== OPS.closeStroke) {
        this.current.tilingPatternDims = null;
      }
      this[op](opIdx, path);
      return;
    }
    if (this.dependencyTracker !== null) {
      const outerExtraSize = op === OPS.stroke ? this.current.lineWidth / 2 : 0;
      this.dependencyTracker.resetBBox(opIdx).recordBBox(opIdx, this.ctx, minMax[0] - outerExtraSize, minMax[2] + outerExtraSize, minMax[1] - outerExtraSize, minMax[3] + outerExtraSize).recordDependencies(opIdx, ["transform"]);
    }
    if (!path) {
      path = makePathFromDrawOPS(data[0]);
      this._pathCache.set(opIdx, path);
    }
    Util.axialAlignedBoundingBox(minMax, getCurrentTransform(this.ctx), this.current.minMax);
    const tilingDims = this.current.tilingPatternDims;
    if (tilingDims && op !== OPS.stroke && op !== OPS.closeStroke && this.current.fillColor instanceof TilingPattern) {
      const clippedBBox = Util.intersect(this.current.clipBox, this.current.minMax);
      if (!clippedBBox) {
        this.current.tilingPatternDims = null;
      } else {
        this.current.fillColor.updatePatternDims(clippedBBox, tilingDims);
      }
    }
    this[op](opIdx, path);
    this._pathStartIdx = opIdx;
  }
  closePath(opIdx) {
    this.ctx.closePath();
  }
  stroke(opIdx, path, consumePath = true) {
    const started = consumePath && this.#beginKnockoutElement(this.current.strokeAlpha);
    const ctx = this.ctx;
    const strokeColor = this.current.strokeColor;
    ctx.globalAlpha = this.current.strokeAlpha;
    if (this.contentVisible) {
      if (typeof strokeColor === "object" && strokeColor?.getPattern) {
        const baseTransform = strokeColor.isModifyingCurrentTransform() ? ctx.getTransform() : null;
        ctx.save();
        ctx.strokeStyle = strokeColor.getPattern(ctx, this, getCurrentTransformInverse(ctx), PathType.STROKE, opIdx);
        if (baseTransform) {
          const newPath = new Path2D();
          newPath.addPath(path, ctx.getTransform().invertSelf().multiplySelf(baseTransform));
          path = newPath;
        }
        this.rescaleAndStroke(path, false);
        ctx.restore();
      } else {
        this.rescaleAndStroke(path, true);
      }
    }
    this.dependencyTracker?.recordDependencies(opIdx, Dependencies.stroke);
    if (consumePath) {
      this.consumePath(opIdx, path, this.current.getClippedPathBoundingBox(PathType.STROKE, getCurrentTransform(this.ctx)));
    }
    ctx.globalAlpha = this.current.fillAlpha;
    this.#endKnockoutElement(started);
  }
  closeStroke(opIdx, path) {
    this.stroke(opIdx, path);
  }
  fill(opIdx, path, consumePath = true) {
    const started = consumePath && this.#beginKnockoutElement(this.current.fillAlpha);
    const ctx = this.ctx;
    const fillColor = this.current.fillColor;
    const isPatternFill = this.current.patternFill;
    let needRestore = false;
    const intersect = this.current.getClippedPathBoundingBox();
    this.dependencyTracker?.recordDependencies(opIdx, Dependencies.fill);
    if (isPatternFill) {
      const dims = this.current.tilingPatternDims;
      const tileIdx = dims && fillColor.canSkipPatternCanvas(dims);
      if (tileIdx) {
        const {
          pendingClip,
          pendingEOFill
        } = this;
        this.pendingClip = null;
        this.pendingEOFill = false;
        fillColor.drawPattern(this, path, pendingEOFill, tileIdx, opIdx);
        this.pendingClip = pendingClip;
        if (consumePath) {
          this.consumePath(opIdx, path, intersect);
        }
        this.current.tilingPatternDims = null;
        this.#endKnockoutElement(started);
        return;
      }
      const baseTransform = fillColor.isModifyingCurrentTransform() ? ctx.getTransform() : null;
      this.dependencyTracker?.save(opIdx);
      ctx.save();
      ctx.fillStyle = fillColor.getPattern(ctx, this, getCurrentTransformInverse(ctx), PathType.FILL, opIdx);
      if (baseTransform) {
        const newPath = new Path2D();
        newPath.addPath(path, ctx.getTransform().invertSelf().multiplySelf(baseTransform));
        path = newPath;
      }
      needRestore = true;
    }
    if (this.contentVisible && intersect !== null) {
      if (this.pendingEOFill) {
        ctx.fill(path, "evenodd");
        this.pendingEOFill = false;
      } else {
        ctx.fill(path);
      }
    }
    if (needRestore) {
      ctx.restore();
      this.dependencyTracker?.restore(opIdx);
    }
    if (consumePath) {
      this.consumePath(opIdx, path, intersect);
    }
    this.#endKnockoutElement(started);
  }
  eoFill(opIdx, path) {
    this.pendingEOFill = true;
    this.fill(opIdx, path);
  }
  fillStroke(opIdx, path) {
    const started = this.#beginKnockoutElement(Math.min(this.current.fillAlpha, this.current.strokeAlpha));
    this.fill(opIdx, path, false);
    this.stroke(opIdx, path, false);
    this.consumePath(opIdx, path);
    this.#endKnockoutElement(started);
  }
  eoFillStroke(opIdx, path) {
    this.pendingEOFill = true;
    this.fillStroke(opIdx, path);
  }
  closeFillStroke(opIdx, path) {
    this.fillStroke(opIdx, path);
  }
  closeEOFillStroke(opIdx, path) {
    this.pendingEOFill = true;
    this.fillStroke(opIdx, path);
  }
  endPath(opIdx, path) {
    this.consumePath(opIdx, path);
  }
  rawFillPath(opIdx, path) {
    const started = this.#beginKnockoutElement(this.current.fillAlpha);
    this.ctx.fill(path);
    this.dependencyTracker?.recordDependencies(opIdx, Dependencies.rawFillPath).recordOperation(opIdx);
    this.#endKnockoutElement(started);
  }
  clip(opIdx) {
    this.dependencyTracker?.recordFutureForcedDependency("clipMode", opIdx);
    this.pendingClip = NORMAL_CLIP;
  }
  eoClip(opIdx) {
    this.dependencyTracker?.recordFutureForcedDependency("clipMode", opIdx);
    this.pendingClip = EO_CLIP;
  }
  beginText(opIdx) {
    this.current.textMatrix = null;
    this.current.textMatrixScale = 1;
    this.current.x = this.current.lineX = 0;
    this.current.y = this.current.lineY = 0;
    this.dependencyTracker?.recordOpenMarker(opIdx).resetIncrementalData("sameLineText").resetIncrementalData("moveText", opIdx);
  }
  endText(opIdx) {
    const paths = this.pendingTextPaths;
    const ctx = this.ctx;
    if (this.dependencyTracker) {
      const {
        dependencyTracker
      } = this;
      if (paths !== undefined) {
        dependencyTracker.recordFutureForcedDependency("textClip", dependencyTracker.getOpenMarker()).recordFutureForcedDependency("textClip", opIdx);
      }
      dependencyTracker.recordCloseMarker(opIdx);
    }
    if (paths !== undefined) {
      const newPath = new Path2D();
      const invTransf = ctx.getTransform().invertSelf();
      for (const {
        transform,
        x,
        y,
        fontSize,
        path
      } of paths) {
        if (!path) {
          continue;
        }
        newPath.addPath(path, new DOMMatrix(transform).preMultiplySelf(invTransf).translate(x, y).scale(fontSize, -fontSize));
      }
      ctx.clip(newPath);
    }
    delete this.pendingTextPaths;
  }
  setCharSpacing(opIdx, spacing) {
    this.dependencyTracker?.recordSimpleData("charSpacing", opIdx);
    this.current.charSpacing = spacing;
  }
  setWordSpacing(opIdx, spacing) {
    this.dependencyTracker?.recordSimpleData("wordSpacing", opIdx);
    this.current.wordSpacing = spacing;
  }
  setHScale(opIdx, scale) {
    this.dependencyTracker?.recordSimpleData("hScale", opIdx);
    this.current.textHScale = scale / 100;
  }
  setLeading(opIdx, leading) {
    this.dependencyTracker?.recordSimpleData("leading", opIdx);
    this.current.leading = -leading;
  }
  setFont(opIdx, fontRefName, size) {
    this.dependencyTracker?.recordSimpleData("font", opIdx).recordSimpleDataFromNamed("fontObj", fontRefName, opIdx);
    const fontObj = this.commonObjs.get(fontRefName);
    const current = this.current;
    if (!fontObj) {
      throw new Error(`Can't find font for ${fontRefName}`);
    }
    current.fontMatrix = fontObj.fontMatrix || FONT_IDENTITY_MATRIX;
    if (current.fontMatrix[0] === 0 || current.fontMatrix[3] === 0) {
      warn("Invalid font matrix for font " + fontRefName);
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
    const typeface = fontObj.systemFontInfo?.css || `"${name}", ${fontObj.fallbackName}`;
    let bold = "normal";
    if (fontObj.black) {
      bold = "900";
    } else if (fontObj.bold) {
      bold = "bold";
    }
    const italic = fontObj.italic ? "italic" : "normal";
    const browserFontSize = MathClamp(size, MIN_FONT_SIZE, MAX_FONT_SIZE);
    this.current.fontSizeScale = size / browserFontSize;
    this.ctx.font = `${italic} ${bold} ${browserFontSize}px ${typeface}`;
  }
  setTextRenderingMode(opIdx, mode) {
    this.dependencyTracker?.recordSimpleData("textRenderingMode", opIdx);
    this.current.textRenderingMode = mode;
  }
  setTextRise(opIdx, rise) {
    this.dependencyTracker?.recordSimpleData("textRise", opIdx);
    this.current.textRise = rise;
  }
  moveText(opIdx, x, y) {
    this.dependencyTracker?.resetIncrementalData("sameLineText").recordIncrementalData("moveText", opIdx);
    this.current.x = this.current.lineX += x;
    this.current.y = this.current.lineY += y;
  }
  setLeadingMoveText(opIdx, x, y) {
    this.setLeading(opIdx, -y);
    this.moveText(opIdx, x, y);
  }
  setTextMatrix(opIdx, matrix) {
    this.dependencyTracker?.resetIncrementalData("sameLineText").recordSimpleData("textMatrix", opIdx);
    const {
      current
    } = this;
    current.textMatrix = matrix;
    current.textMatrixScale = Math.hypot(matrix[0], matrix[1]);
    current.x = current.lineX = 0;
    current.y = current.lineY = 0;
  }
  nextLine(opIdx) {
    this.moveText(opIdx, 0, this.current.leading);
    this.dependencyTracker?.recordIncrementalData("moveText", this.dependencyTracker.getSimpleIndex("leading") ?? opIdx);
  }
  #getScaledPath(path, currentTransform, transform) {
    const newPath = new Path2D();
    newPath.addPath(path, new DOMMatrix(transform).invertSelf().multiplySelf(currentTransform));
    return newPath;
  }
  paintChar(opIdx, character, x, y, patternFillTransform, patternStrokeTransform) {
    const ctx = this.ctx;
    const current = this.current;
    const font = current.font;
    const textRenderingMode = current.textRenderingMode;
    const fontSize = current.fontSize / current.fontSizeScale;
    const fillStrokeMode = textRenderingMode & TextRenderingMode.FILL_STROKE_MASK;
    const isAddToPathSet = !!(textRenderingMode & TextRenderingMode.ADD_TO_PATH_FLAG);
    const patternFill = current.patternFill && !font.missingFile;
    const patternStroke = current.patternStroke && !font.missingFile;
    let path;
    if ((font.disableFontFace || isAddToPathSet || patternFill || patternStroke) && !font.missingFile) {
      path = font.getPathGenerator(this.commonObjs, character);
    }
    if (path && (font.disableFontFace || patternFill || patternStroke)) {
      ctx.save();
      ctx.translate(x, y);
      ctx.scale(fontSize, -fontSize);
      this.dependencyTracker?.recordCharacterBBox(opIdx, ctx, font);
      let currentTransform;
      if (fillStrokeMode === TextRenderingMode.FILL || fillStrokeMode === TextRenderingMode.FILL_STROKE) {
        if (patternFillTransform) {
          currentTransform = ctx.getTransform();
          ctx.setTransform(...patternFillTransform);
          const scaledPath = this.#getScaledPath(path, currentTransform, patternFillTransform);
          ctx.fill(scaledPath);
        } else {
          ctx.fill(path);
        }
      }
      if (fillStrokeMode === TextRenderingMode.STROKE || fillStrokeMode === TextRenderingMode.FILL_STROKE) {
        if (patternStrokeTransform) {
          currentTransform ||= ctx.getTransform();
          ctx.setTransform(...patternStrokeTransform);
          const {
            a,
            b,
            c,
            d
          } = currentTransform;
          const invPatternTransform = Util.inverseTransform(patternStrokeTransform);
          const transf = Util.transform([a, b, c, d, 0, 0], invPatternTransform);
          Util.singularValueDecompose2dScale(transf, XY);
          ctx.lineWidth *= Math.max(XY[0], XY[1]) / fontSize;
          ctx.stroke(this.#getScaledPath(path, currentTransform, patternStrokeTransform));
        } else {
          ctx.lineWidth /= fontSize;
          ctx.stroke(path);
        }
      }
      ctx.restore();
    } else {
      if (fillStrokeMode === TextRenderingMode.FILL || fillStrokeMode === TextRenderingMode.FILL_STROKE) {
        ctx.fillText(character, x, y);
        this.dependencyTracker?.recordCharacterBBox(opIdx, ctx, font, fontSize, x, y, () => ctx.measureText(character));
      }
      if (fillStrokeMode === TextRenderingMode.STROKE || fillStrokeMode === TextRenderingMode.FILL_STROKE) {
        if (this.dependencyTracker) {
          this.dependencyTracker?.recordCharacterBBox(opIdx, ctx, font, fontSize, x, y, () => ctx.measureText(character)).recordDependencies(opIdx, Dependencies.stroke);
        }
        ctx.strokeText(character, x, y);
      }
    }
    if (isAddToPathSet) {
      const paths = this.pendingTextPaths ||= [];
      paths.push({
        transform: getCurrentTransform(ctx),
        x,
        y,
        fontSize,
        path
      });
      this.dependencyTracker?.recordCharacterBBox(opIdx, ctx, font, fontSize, x, y);
    }
  }
  get isFontSubpixelAAEnabled() {
    const tmpCanvas = this.canvasFactory.create(10, 10);
    const ctx = tmpCanvas.context;
    ctx.scale(1.5, 1);
    ctx.fillText("I", 0, 10);
    const data = ctx.getImageData(0, 0, 10, 10).data;
    this.canvasFactory.destroy(tmpCanvas);
    let enabled = false;
    for (let i = 3; i < data.length; i += 4) {
      if (data[i] > 0 && data[i] < 255) {
        enabled = true;
        break;
      }
    }
    return shadow(this, "isFontSubpixelAAEnabled", enabled);
  }
  #getTextPattern(color, pathType, opIdx) {
    const ctx = this.ctx;
    ctx.save();
    const pattern = color.getPattern(ctx, this, getCurrentTransformInverse(ctx), pathType, opIdx);
    const transform = getCurrentTransform(ctx);
    ctx.restore();
    return [pattern, transform];
  }
  showText(opIdx, glyphs) {
    if (this.dependencyTracker) {
      this.dependencyTracker.recordDependencies(opIdx, Dependencies.showText).resetBBox(opIdx);
      if (this.current.textRenderingMode & TextRenderingMode.ADD_TO_PATH_FLAG) {
        this.dependencyTracker.recordFutureForcedDependency("textClip", opIdx).inheritPendingDependenciesAsFutureForcedDependencies();
      }
    }
    const current = this.current;
    const font = current.font;
    if (font.isType3Font) {
      const started = this.#beginKnockoutElement(current.fillAlpha);
      this.showType3Text(opIdx, glyphs);
      this.dependencyTracker?.recordShowTextOperation(opIdx);
      this.#endKnockoutElement(started);
      return;
    }
    const fontSize = current.fontSize;
    if (fontSize === 0) {
      this.dependencyTracker?.recordOperation(opIdx);
      return;
    }
    const started = this.#beginKnockoutElement(current.fillAlpha);
    const ctx = this.ctx;
    const fontSizeScale = current.fontSizeScale;
    const charSpacing = current.charSpacing;
    const wordSpacing = current.wordSpacing;
    const fontDirection = current.fontDirection;
    const textHScale = current.textHScale * fontDirection;
    const glyphsLength = glyphs.length;
    const vertical = font.vertical;
    const spacingDir = vertical ? 1 : -1;
    const widthAdvanceScale = fontSize * current.fontMatrix[0];
    const simpleFillText = current.textRenderingMode === TextRenderingMode.FILL && !font.disableFontFace && !current.patternFill;
    ctx.save();
    if (current.textMatrix) {
      ctx.transform(...current.textMatrix);
    }
    ctx.translate(current.x, current.y + current.textRise);
    if (fontDirection > 0) {
      ctx.scale(textHScale, -1);
    } else {
      ctx.scale(textHScale, 1);
    }
    let patternFillTransform, patternStrokeTransform;
    const fillStrokeMode = current.textRenderingMode & TextRenderingMode.FILL_STROKE_MASK;
    const needsFill = fillStrokeMode === TextRenderingMode.FILL || fillStrokeMode === TextRenderingMode.FILL_STROKE;
    const needsStroke = fillStrokeMode === TextRenderingMode.STROKE || fillStrokeMode === TextRenderingMode.FILL_STROKE;
    let lineWidth = current.lineWidth;
    const scale = current.textMatrixScale;
    if (scale === 0 || lineWidth === 0) {
      if (needsStroke) {
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
    if (needsFill && current.patternFill) {
      [ctx.fillStyle, patternFillTransform] = this.#getTextPattern(current.fillColor, PathType.FILL, opIdx);
    }
    if (needsStroke && current.patternStroke) {
      [ctx.strokeStyle, patternStrokeTransform] = this.#getTextPattern(current.strokeColor, PathType.STROKE, opIdx);
    }
    if (font.isInvalidPDFjsFont) {
      const chars = [];
      let width = 0;
      for (const glyph of glyphs) {
        chars.push(glyph.unicode);
        width += glyph.width;
      }
      const joinedChars = chars.join("");
      ctx.fillText(joinedChars, 0, 0);
      if (this.dependencyTracker !== null) {
        const measure = ctx.measureText(joinedChars);
        this.dependencyTracker.recordBBox(opIdx, this.ctx, -measure.actualBoundingBoxLeft, measure.actualBoundingBoxRight, -measure.actualBoundingBoxAscent, measure.actualBoundingBoxDescent).recordShowTextOperation(opIdx);
      }
      current.x += width * widthAdvanceScale * textHScale;
      ctx.restore();
      this.compose();
      this.#endKnockoutElement(started);
      return;
    }
    let x = 0,
      i,
      glyphPatterns = null;
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
      let scaledX, scaledY, measure;
      let width = glyph.width;
      if (vertical) {
        const vmetric = glyph.vmetric;
        const vx = -vmetric[1] * widthAdvanceScale;
        const vy = vmetric[2] * widthAdvanceScale;
        width = -vmetric[0];
        scaledX = vx / fontSizeScale;
        scaledY = (x + vy) / fontSizeScale;
        if (glyph.isRotated) {
          measure = ctx.measureText(character);
          const glyphScale = widthAdvanceScale / fontSizeScale;
          const halfWidth = glyph.width / 2 * glyphScale;
          const centerX = scaledX + halfWidth;
          scaledX = scaledY - ((/* inlined export .DEFAULT_VERTICAL_ORIGIN_Y */880) - (/* inlined export .DEFAULT_VERTICAL_ADVANCE */1000) / 2) * glyphScale - halfWidth;
          scaledY = (measure.actualBoundingBoxAscent - measure.actualBoundingBoxDescent) / 2 - centerX;
          restoreNeeded = true;
          ctx.save();
          ctx.rotate(Math.PI / 2);
        }
      } else {
        scaledX = x / fontSizeScale;
        scaledY = 0;
      }
      const glyphWidth = glyph.isRotated ? glyph.width : width;
      let characterScaleX = 1;
      if ((font.remeasure || glyph.isRotated) && glyphWidth > 0) {
        measure ??= ctx.measureText(character);
        const measuredWidth = measure.width * 1000 / fontSize * fontSizeScale;
        if (glyphWidth < measuredWidth && this.isFontSubpixelAAEnabled) {
          characterScaleX = glyphWidth / measuredWidth;
          if (!restoreNeeded) {
            restoreNeeded = true;
            ctx.save();
          }
          ctx.scale(characterScaleX, 1);
          scaledX /= characterScaleX;
        } else if (glyphWidth !== measuredWidth) {
          scaledX += (glyphWidth - measuredWidth) / 2000 * fontSize / fontSizeScale;
        }
      }
      if (restoreNeeded && font.missingFile && (patternFillTransform || patternStrokeTransform)) {
        glyphPatterns ||= new Map();
        [ctx.fillStyle, ctx.strokeStyle] = glyphPatterns.getOrInsertComputed(glyph.isRotated ? -characterScaleX : characterScaleX, () => [patternFillTransform ? this.#getTextPattern(current.fillColor, PathType.FILL, opIdx)[0] : ctx.fillStyle, patternStrokeTransform ? this.#getTextPattern(current.strokeColor, PathType.STROKE, opIdx)[0] : ctx.strokeStyle]);
      }
      if (this.contentVisible && (glyph.isInFont || font.missingFile)) {
        if (simpleFillText && !accent) {
          ctx.fillText(character, scaledX, scaledY);
          this.dependencyTracker?.recordCharacterBBox(opIdx, ctx, measure ? {
            bbox: null
          } : font, fontSize / fontSizeScale, scaledX, scaledY, () => measure ?? ctx.measureText(character));
        } else {
          this.paintChar(opIdx, character, scaledX, scaledY, patternFillTransform, patternStrokeTransform);
          if (accent) {
            const scaledAccentX = scaledX + fontSize * accent.offset.x / fontSizeScale;
            const scaledAccentY = scaledY - fontSize * accent.offset.y / fontSizeScale;
            this.paintChar(opIdx, accent.fontChar, scaledAccentX, scaledAccentY, patternFillTransform, patternStrokeTransform);
          }
        }
      }
      const charWidth = vertical ? width * widthAdvanceScale - spacing * fontDirection : width * widthAdvanceScale + spacing * fontDirection;
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
    this.dependencyTracker?.recordShowTextOperation(opIdx);
    this.#endKnockoutElement(started);
  }
  showType3Text(opIdx, glyphs) {
    const ctx = this.ctx;
    const current = this.current;
    const font = current.font;
    const fontSize = current.fontSize;
    const fontDirection = current.fontDirection;
    const spacingDir = font.vertical ? 1 : -1;
    const charSpacing = current.charSpacing;
    const wordSpacing = current.wordSpacing;
    const textHScale = current.textHScale * fontDirection;
    const fontMatrix = current.fontMatrix || FONT_IDENTITY_MATRIX;
    const glyphsLength = glyphs.length;
    const isTextVisible = current.textRenderingMode !== TextRenderingMode.INVISIBLE;
    let i, glyph, width, spacingLength;
    if (fontSize === 0) {
      return;
    }
    this._cachedScaleForStroking[0] = -1;
    ctx.save();
    if (current.textMatrix) {
      ctx.transform(...current.textMatrix);
    }
    ctx.translate(current.x, current.y + current.textRise);
    ctx.scale(textHScale, fontDirection);
    const dependencyTracker = this.dependencyTracker;
    this.dependencyTracker = dependencyTracker ? new CanvasNestedDependencyTracker(dependencyTracker, opIdx) : null;
    try {
      for (i = 0; i < glyphsLength; ++i) {
        glyph = glyphs[i];
        if (typeof glyph === "number") {
          spacingLength = spacingDir * glyph * fontSize / 1000;
          this.ctx.translate(spacingLength, 0);
          current.x += spacingLength * textHScale;
          continue;
        }
        const spacing = (glyph.isSpace ? wordSpacing : 0) + charSpacing;
        const operatorList = font.charProcOperatorList.get(glyph.operatorListId);
        if (!operatorList) {
          warn(`Type3 character "${glyph.operatorListId}" is not available.`);
        } else if (this.contentVisible && isTextVisible) {
          this.save();
          ctx.scale(fontSize, fontSize);
          ctx.transform(...fontMatrix);
          this.executeOperatorList(operatorList);
          this.restore();
        }
        width = glyph.width * fontMatrix[0] * fontSize + spacing * fontDirection;
        ctx.translate(width, 0);
        current.x += width * textHScale;
      }
    } finally {
      if (dependencyTracker) {
        this.dependencyTracker = dependencyTracker;
      }
    }
    ctx.restore();
  }
  setCharWidth(opIdx, xWidth, yWidth) {}
  setCharWidthAndBounds(opIdx, xWidth, yWidth, llx, lly, urx, ury) {
    const clip = new Path2D();
    clip.rect(llx, lly, urx - llx, ury - lly);
    this.ctx.clip(clip);
    this.dependencyTracker?.recordBBox(opIdx, this.ctx, llx, urx, lly, ury).recordClipBox(opIdx, this.ctx, llx, urx, lly, ury);
    this.endPath(opIdx);
  }
  getColorN_Pattern(opIdx, IR) {
    let pattern;
    if (IR[0] === "TilingPattern") {
      const baseTransform = this.baseTransform || getCurrentTransform(this.ctx);
      const canvasGraphicsFactory = {
        createCanvasGraphics: (ctx, renderingOpIdx) => new CanvasGraphics(ctx, this.commonObjs, this.objs, this.canvasFactory, this.filterFactory, {
          optionalContentConfig: this.optionalContentConfig,
          markedContentStack: this.markedContentStack,
          pixelRatio: this.pixelRatio
        }, undefined, undefined, this.dependencyTracker ? new CanvasNestedDependencyTracker(this.dependencyTracker, renderingOpIdx, true) : null)
      };
      pattern = new TilingPattern(IR, this.ctx, canvasGraphicsFactory, baseTransform);
    } else {
      pattern = this._getPattern(opIdx, IR[1], IR[2]);
    }
    return pattern;
  }
  setStrokeColorN(opIdx, ...args) {
    this.dependencyTracker?.recordSimpleData("strokeColor", opIdx);
    this.current.strokeColor = this.getColorN_Pattern(opIdx, args);
    this.current.patternStroke = true;
  }
  setFillColorN(opIdx, ...args) {
    this.dependencyTracker?.recordSimpleData("fillColor", opIdx);
    const pattern = this.current.fillColor = this.getColorN_Pattern(opIdx, args);
    this.current.patternFill = true;
    this.current.tilingPatternDims = pattern instanceof TilingPattern ? [0, 0, 0, 0] : null;
  }
  #transferColor(color) {
    return this.current.transferMapsFallback?.applyToColor(color) ?? color;
  }
  setStrokeRGBColor(opIdx, color) {
    this.dependencyTracker?.recordSimpleData("strokeColor", opIdx);
    this.current.strokeColor = color;
    this.ctx.strokeStyle = this.#transferColor(color);
    this.current.patternStroke = false;
  }
  setStrokeTransparent(opIdx) {
    this.dependencyTracker?.recordSimpleData("strokeColor", opIdx);
    this.ctx.strokeStyle = this.current.strokeColor = "transparent";
    this.current.patternStroke = false;
  }
  setFillRGBColor(opIdx, color) {
    this.dependencyTracker?.recordSimpleData("fillColor", opIdx);
    this.current.fillColor = color;
    this.ctx.fillStyle = this.#transferColor(color);
    this.current.patternFill = false;
    this.current.tilingPatternDims = null;
  }
  setFillTransparent(opIdx) {
    this.dependencyTracker?.recordSimpleData("fillColor", opIdx);
    this.ctx.fillStyle = this.current.fillColor = "transparent";
    this.current.patternFill = false;
    this.current.tilingPatternDims = null;
  }
  _getPattern(opIdx, objId, matrix = null) {
    const pattern = this.cachedPatterns.getOrInsertComputed(objId, () => getShadingPattern(this.getObject(opIdx, objId)));
    if (matrix) {
      pattern.matrix = matrix;
    }
    return pattern;
  }
  shadingFill(opIdx, objId) {
    if (!this.contentVisible) {
      return;
    }
    const started = this.#beginKnockoutElement(this.current.fillAlpha);
    const ctx = this.ctx;
    this.save(opIdx);
    const pattern = this._getPattern(opIdx, objId);
    ctx.fillStyle = pattern.getPattern(ctx, this, getCurrentTransformInverse(ctx), PathType.SHADING, opIdx);
    const inv = getCurrentTransformInverse(ctx);
    if (inv) {
      const {
        width,
        height
      } = ctx.canvas;
      const minMax = F32_BBOX_INIT.slice();
      Util.axialAlignedBoundingBox([0, 0, width, height], inv, minMax);
      const [x0, y0, x1, y1] = minMax;
      this.ctx.fillRect(x0, y0, x1 - x0, y1 - y0);
    } else {
      this.ctx.fillRect(-1e10, -1e10, 2e10, 2e10);
    }
    this.dependencyTracker?.resetBBox(opIdx).recordFullPageBBox(opIdx).recordDependencies(opIdx, Dependencies.transform).recordDependencies(opIdx, Dependencies.fill).recordOperation(opIdx);
    this.compose(this.current.getClippedPathBoundingBox());
    this.restore(opIdx);
    this.#endKnockoutElement(started);
  }
  beginInlineImage() {
    unreachable("Should not call beginInlineImage");
  }
  beginImageData() {
    unreachable("Should not call beginImageData");
  }
  paintFormXObjectBegin(opIdx, matrix, bbox) {
    if (!this.contentVisible) {
      return;
    }
    this.save(opIdx);
    this.baseTransformStack.push(this.baseTransform);
    if (matrix) {
      this.transform(opIdx, ...matrix);
    }
    this.baseTransform = getCurrentTransform(this.ctx);
    if (bbox) {
      Util.axialAlignedBoundingBox(bbox, this.baseTransform, this.current.minMax);
      const [x0, y0, x1, y1] = bbox;
      const clip = new Path2D();
      clip.rect(x0, y0, x1 - x0, y1 - y0);
      this.ctx.clip(clip);
      this.dependencyTracker?.recordClipBox(opIdx, this.ctx, x0, x1, y0, y1);
      this.endPath(opIdx);
    }
  }
  paintFormXObjectEnd(opIdx) {
    if (!this.contentVisible) {
      return;
    }
    this.restore(opIdx);
    this.baseTransform = this.baseTransformStack.pop();
  }
  beginGroup(opIdx, group) {
    if (!this.contentVisible) {
      return;
    }
    this.save(opIdx);
    const {
      inSMaskMode
    } = this;
    if (inSMaskMode) {
      this.endSMaskMode();
      this.current.activeSMask = null;
    }
    const currentCtx = this.ctx;
    if ((!group.needsIsolation || !group.isolated && !group.hasSoftMask) && !group.knockout && !group.isGray && this.#knockoutGroupLevel === 0 && currentCtx.globalAlpha === 1 && currentCtx.globalCompositeOperation === "source-over" && !inSMaskMode) {
      if (group.bbox) {
        let clip = new Path2D();
        const [x0, y0, x1, y1] = group.bbox;
        clip.rect(x0, y0, x1 - x0, y1 - y0);
        if (group.matrix) {
          const path = new Path2D();
          path.addPath(clip, new DOMMatrix(group.matrix));
          clip = path;
        }
        currentCtx.clip(clip);
      }
      this.groupStack.push(null);
      this.#groupStackMeta.push(null);
      this.groupLevel++;
      return;
    }
    if (!group.isolated && !group.knockout && this.#knockoutGroupLevel === 0) {
      info("TODO: Fully support non-isolated non-knockout groups.");
    }
    const currentTransform = getCurrentTransform(currentCtx);
    if (group.matrix) {
      currentCtx.transform(...group.matrix);
    }
    const canvasBounds = [0, 0, currentCtx.canvas.width, currentCtx.canvas.height];
    let bounds;
    if (group.bbox) {
      bounds = F32_BBOX_INIT.slice();
      Util.axialAlignedBoundingBox(group.bbox, getCurrentTransform(currentCtx), bounds);
      bounds = Util.intersect(bounds, canvasBounds) || [0, 0, 0, 0];
    } else {
      bounds = canvasBounds;
    }
    const offsetX = Math.floor(bounds[0]);
    const offsetY = Math.floor(bounds[1]);
    const drawnWidth = Math.max(Math.ceil(bounds[2]) - offsetX, 1);
    const drawnHeight = Math.max(Math.ceil(bounds[3]) - offsetY, 1);
    this.current.startNewPathAndClipBox([0, 0, drawnWidth, drawnHeight]);
    const scratchCanvas = this.canvasFactory.create(drawnWidth, drawnHeight);
    if (group.smask) {
      this.smaskGroupCanvases.push(scratchCanvas);
    }
    const groupCtx = scratchCanvas.context;
    const backdropCtx = group.knockout && !group.isolated ? currentCtx : null;
    const hasInnerBackdrop = !group.isolated && !group.knockout && !group.smask && group.needsIsolation && this.#knockoutGroupLevel > 0;
    const knockoutMaskEntry = group.knockout ? this.canvasFactory.create(drawnWidth, drawnHeight) : null;
    const savedKnockoutLevel = this.#knockoutGroupLevel;
    if (group.knockout) {
      this.#knockoutGroupLevel++;
    } else {
      this.#knockoutGroupLevel = 0;
    }
    groupCtx.translate(-offsetX, -offsetY);
    groupCtx.transform(...currentTransform);
    const needsBackdropCopy = !group.isolated && !group.smask && group.needsIsolation;
    const replaceBackdrop = needsBackdropCopy && !inSMaskMode && savedKnockoutLevel === 0 && !group.knockout && !group.isGray && group.hasSoftMask && currentCtx.globalAlpha === 1 && currentCtx.globalCompositeOperation === "source-over" && this.current.transferMaps === "none" && !this.current.transferMapsFallback;
    if (needsBackdropCopy && (inSMaskMode || replaceBackdrop)) {
      groupCtx.save();
      groupCtx.setTransform(1, 0, 0, 1, 0, 0);
      groupCtx.drawImage(currentCtx.canvas, -offsetX, -offsetY);
      groupCtx.restore();
    }
    if (group.bbox) {
      let clip = new Path2D();
      const [x0, y0, x1, y1] = group.bbox;
      clip.rect(x0, y0, x1 - x0, y1 - y0);
      if (group.matrix) {
        const path = new Path2D();
        path.addPath(clip, new DOMMatrix(group.matrix));
        clip = path;
      }
      groupCtx.clip(clip);
    }
    if (group.smask) {
      this.smaskStack.push({
        canvas: scratchCanvas.canvas,
        context: groupCtx,
        offsetX,
        offsetY,
        subtype: group.smask.subtype,
        backdrop: group.smask.backdrop,
        transferMap: group.smask.transferMap || null
      });
    }
    if (!group.smask || this.dependencyTracker) {
      currentCtx.setTransform(1, 0, 0, 1, 0, 0);
      currentCtx.translate(offsetX, offsetY);
      currentCtx.save();
    }
    copyCtxState(currentCtx, groupCtx);
    this.ctx = groupCtx;
    this.dependencyTracker?.inheritSimpleDataAsFutureForcedDependencies(["fillAlpha", "strokeAlpha", "globalCompositeOperation"]).pushBaseTransform(currentCtx);
    this.setGState(opIdx, [["BM", "source-over"], ["ca", 1], ["CA", 1], ["TR", null]]);
    this.groupStack.push(currentCtx);
    this.#groupStackMeta.push({
      backdropCtx,
      savedKnockoutLevel,
      offsetX,
      offsetY,
      hasInnerBackdrop,
      replaceBackdrop,
      knockoutMaskEntry,
      knockoutTempEntry: null,
      knockoutBackdropEntry: null
    });
    this.groupLevel++;
  }
  endGroup(opIdx, group) {
    if (!this.contentVisible) {
      return;
    }
    this.groupLevel--;
    const groupCtx = this.ctx;
    const ctx = this.groupStack.pop();
    const groupMeta = this.#groupStackMeta.pop();
    if (groupMeta) {
      this.#knockoutGroupLevel = groupMeta.savedKnockoutLevel;
    }
    if (ctx === null) {
      this.restore(opIdx);
      return;
    }
    if (group.isGray) {
      this.#convertGroupToGray(groupCtx);
    }
    this.ctx = ctx;
    this.ctx.imageSmoothingEnabled = false;
    this.dependencyTracker?.popBaseTransform();
    if (group.smask) {
      this.tempSMask = this.smaskStack.pop();
      this.restore(opIdx);
      if (this.dependencyTracker) {
        this.ctx.restore();
        if (this.inSMaskMode) {
          this.ctx.setTransform(this.suspendedCtx.getTransform());
        }
      }
      this.#destroyKnockoutPools(groupMeta);
    } else {
      this.ctx.restore();
      const currentMtx = getCurrentTransform(this.ctx);
      this.restore(opIdx);
      this.current.transferMapsFallback?.applyToCanvas(groupCtx);
      this.ctx.save();
      this.ctx.setTransform(...currentMtx);
      const dirtyBox = F32_BBOX_INIT.slice();
      Util.axialAlignedBoundingBox([0, 0, groupCtx.canvas.width, groupCtx.canvas.height], currentMtx, dirtyBox);
      const parentGroupMeta = this.#groupStackMeta.at(-1);
      if (this.#knockoutGroupLevel > 0) {
        if (groupMeta.hasInnerBackdrop) {
          const {
            width,
            height
          } = groupCtx.canvas;
          const colorEntry = this.canvasFactory.create(width, height);
          const colorCtx = colorEntry.context;
          colorCtx.drawImage(ctx.canvas, groupMeta.offsetX, groupMeta.offsetY, width, height, 0, 0, width, height);
          colorCtx.globalCompositeOperation = "source-over";
          colorCtx.drawImage(groupCtx.canvas, 0, 0);
          const shapeMaskEntry = this.#createKnockoutMaskCanvas(groupCtx.canvas);
          colorCtx.globalCompositeOperation = "destination-in";
          colorCtx.drawImage(shapeMaskEntry.canvas, 0, 0);
          const sourceCompositeOperation = this.ctx.globalCompositeOperation;
          const sourceAlpha = this.ctx.globalAlpha;
          const sourceFilter = this.ctx.filter;
          this.ctx.save();
          this.ctx.setTransform(...currentMtx);
          this.ctx.globalAlpha = 1;
          if (FeatureTest.isCanvasFilterSupported) {
            this.ctx.filter = "none";
          }
          this.ctx.globalCompositeOperation = "destination-out";
          this.ctx.drawImage(shapeMaskEntry.canvas, 0, 0);
          this.ctx.globalCompositeOperation = sourceCompositeOperation;
          this.ctx.globalAlpha = sourceAlpha;
          if (FeatureTest.isCanvasFilterSupported) {
            this.ctx.filter = sourceFilter ?? "none";
          }
          this.ctx.drawImage(colorEntry.canvas, 0, 0);
          this.ctx.restore();
          this.canvasFactory.destroy(shapeMaskEntry);
          this.canvasFactory.destroy(colorEntry);
        } else {
          const backdropCtx = parentGroupMeta?.backdropCtx ?? null;
          this.#compositeKnockoutSurface(this.ctx, groupCtx.canvas, {
            backdropCanvas: backdropCtx?.canvas ?? null,
            destTransform: currentMtx,
            backdropOffset: backdropCtx ? [parentGroupMeta.offsetX + groupMeta.offsetX, parentGroupMeta.offsetY + groupMeta.offsetY] : [0, 0],
            sourceAlpha: this.ctx.globalAlpha,
            sourceFilter: this.ctx.filter
          });
        }
      } else {
        if (groupMeta.replaceBackdrop) {
          const clip = new Path2D();
          clip.rect(0, 0, groupCtx.canvas.width, groupCtx.canvas.height);
          this.ctx.clip(clip);
          this.ctx.globalCompositeOperation = "copy";
        }
        this.ctx.drawImage(groupCtx.canvas, 0, 0);
      }
      this.ctx.restore();
      this.canvasFactory.destroy({
        canvas: groupCtx.canvas,
        context: groupCtx
      });
      this.#destroyKnockoutPools(groupMeta);
      this.compose(dirtyBox);
    }
  }
  #convertGroupToGray(groupCtx) {
    const {
      canvas
    } = groupCtx;
    const {
      width,
      height
    } = canvas;
    if (FeatureTest.isCanvasFilterSupported) {
      groupCtx.save();
      groupCtx.setTransform(1, 0, 0, 1, 0, 0);
      groupCtx.filter = "grayscale(1)";
      groupCtx.globalAlpha = 1;
      groupCtx.globalCompositeOperation = "copy";
      groupCtx.drawImage(canvas, 0, 0);
      groupCtx.restore();
      return;
    }
    const imageData = groupCtx.getImageData(0, 0, width, height);
    const {
      data
    } = imageData;
    for (let i = 0, ii = data.length; i < ii; i += 4) {
      const gray = data[i] * 0.2126 + data[i + 1] * 0.7152 + data[i + 2] * 0.0722 + 0.5 | 0;
      data[i] = data[i + 1] = data[i + 2] = gray;
    }
    groupCtx.putImageData(imageData, 0, 0);
  }
  #destroyKnockoutPools(groupMeta) {
    if (!groupMeta) {
      return;
    }
    if (groupMeta.knockoutMaskEntry) {
      this.canvasFactory.destroy(groupMeta.knockoutMaskEntry);
      groupMeta.knockoutMaskEntry = null;
    }
    if (groupMeta.knockoutTempEntry) {
      this.canvasFactory.destroy(groupMeta.knockoutTempEntry);
      groupMeta.knockoutTempEntry = null;
    }
    if (groupMeta.knockoutBackdropEntry) {
      this.canvasFactory.destroy(groupMeta.knockoutBackdropEntry);
      groupMeta.knockoutBackdropEntry = null;
    }
  }
  beginAnnotation(opIdx, id, rect, transform, matrix, hasOwnCanvas, canvasName) {
    this.#restoreInitialState();
    resetCtxToDefault(this.ctx);
    this.ctx.save();
    this.save(opIdx);
    if (this.baseTransform) {
      this.ctx.setTransform(...this.baseTransform);
    }
    if (rect) {
      const width = rect[2] - rect[0];
      const height = rect[3] - rect[1];
      if (hasOwnCanvas && this.annotationCanvasMap) {
        transform = transform.slice();
        transform[4] -= rect[0];
        transform[5] -= rect[1];
        Util.singularValueDecompose2dScale(getCurrentTransform(this.ctx), XY);
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
        if (canvasName) {
          const canvases = this.annotationCanvasMap.getOrInsertComputed(id, makeArr);
          setAnnotationCanvasName(canvas, canvasName);
          const index = canvases.findIndex(c => getAnnotationCanvasName(c) === canvasName);
          if (index === -1) {
            canvases.push(canvas);
          } else {
            canvases[index] = canvas;
          }
        } else {
          this.annotationCanvasMap.set(id, canvas);
        }
        this.annotationCanvas.savedCtx = this.ctx;
        this.ctx = context;
        this.ctx.save();
        this.ctx.setTransform(XY[0], 0, 0, -XY[1], 0, height * XY[1]);
        resetCtxToDefault(this.ctx);
      } else {
        resetCtxToDefault(this.ctx);
        this.endPath(opIdx);
        const clip = new Path2D();
        clip.rect(rect[0], rect[1], width, height);
        this.ctx.clip(clip);
      }
    }
    this.current = new CanvasExtraState(this.ctx.canvas.width, this.ctx.canvas.height);
    this.baseTransformStack.push(this.baseTransform);
    this.transform(opIdx, ...transform);
    this.transform(opIdx, ...matrix);
    this.baseTransform = getCurrentTransform(this.ctx);
  }
  endAnnotation(opIdx) {
    if (this.annotationCanvas) {
      this.ctx.restore();
      this.#drawFilter();
      this.ctx = this.annotationCanvas.savedCtx;
      delete this.annotationCanvas.savedCtx;
      delete this.annotationCanvas;
    }
    this.baseTransform = this.baseTransformStack.pop();
  }
  paintImageMaskXObject(opIdx, img) {
    if (!this.contentVisible) {
      return;
    }
    const count = img.count;
    img = this.getObject(opIdx, img.data, img);
    img.count = count;
    const started = this.#beginKnockoutElement(this.current.fillAlpha);
    const ctx = this.ctx;
    const mask = this._createMaskCanvas(opIdx, img);
    const maskCanvas = mask.canvas;
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.drawImage(maskCanvas, mask.offsetX, mask.offsetY);
    this.dependencyTracker?.resetBBox(opIdx).recordBBox(opIdx, this.ctx, mask.offsetX, mask.offsetX + maskCanvas.width, mask.offsetY, mask.offsetY + maskCanvas.height).recordOperation(opIdx);
    ctx.restore();
    if (mask.canvasEntry) {
      this.canvasFactory.destroy(mask.canvasEntry);
    }
    this.compose();
    this.#endKnockoutElement(started);
  }
  paintImageMaskXObjectRepeat(opIdx, img, scaleX, skewX = 0, skewY = 0, scaleY, positions) {
    if (!this.contentVisible) {
      return;
    }
    img = this.getObject(opIdx, img.data, img);
    const started = this.#beginKnockoutElement(this.current.fillAlpha);
    const ctx = this.ctx;
    ctx.save();
    const currentTransform = getCurrentTransform(ctx);
    ctx.transform(scaleX, skewX, skewY, scaleY, 0, 0);
    const mask = this._createMaskCanvas(opIdx, img);
    ctx.setTransform(1, 0, 0, 1, mask.offsetX - currentTransform[4], mask.offsetY - currentTransform[5]);
    this.dependencyTracker?.resetBBox(opIdx);
    for (let i = 0, ii = positions.length; i < ii; i += 2) {
      const trans = Util.transform(currentTransform, [scaleX, skewX, skewY, scaleY, positions[i], positions[i + 1]]);
      ctx.drawImage(mask.canvas, trans[4], trans[5]);
      this.dependencyTracker?.recordBBox(opIdx, this.ctx, trans[4], trans[4] + mask.canvas.width, trans[5], trans[5] + mask.canvas.height);
    }
    ctx.restore();
    if (mask.canvasEntry) {
      this.canvasFactory.destroy(mask.canvasEntry);
    }
    this.compose();
    this.dependencyTracker?.recordOperation(opIdx);
    this.#endKnockoutElement(started);
  }
  paintImageMaskXObjectGroup(opIdx, images) {
    if (!this.contentVisible) {
      return;
    }
    const started = this.#beginKnockoutElement(this.current.fillAlpha);
    const ctx = this.ctx;
    const isPatternFill = this.current.patternFill;
    const fillColor = isPatternFill ? this.current.fillColor : ctx.fillStyle;
    this.dependencyTracker?.resetBBox(opIdx).recordDependencies(opIdx, Dependencies.transformAndFill);
    for (const image of images) {
      const {
        data,
        width,
        height,
        transform
      } = image;
      const maskCanvas = this.canvasFactory.create(width, height);
      const maskCtx = maskCanvas.context;
      maskCtx.save();
      const img = this.getObject(opIdx, data, image);
      putBinaryImageMask(maskCtx, img);
      maskCtx.globalCompositeOperation = "source-in";
      maskCtx.fillStyle = isPatternFill ? fillColor.getPattern(maskCtx, this, getCurrentTransformInverse(ctx), PathType.FILL, opIdx) : fillColor;
      maskCtx.fillRect(0, 0, width, height);
      maskCtx.restore();
      ctx.save();
      ctx.transform(...transform);
      ctx.scale(1, -1);
      drawImageAtIntegerCoords(ctx, maskCanvas.canvas, 0, 0, width, height, 0, -1, 1, 1);
      this.canvasFactory.destroy(maskCanvas);
      this.dependencyTracker?.recordBBox(opIdx, ctx, 0, width, 0, height);
      ctx.restore();
    }
    this.compose();
    this.dependencyTracker?.recordOperation(opIdx);
    this.#endKnockoutElement(started);
  }
  paintImageXObject(opIdx, objId) {
    if (!this.contentVisible) {
      return;
    }
    const imgData = this.getObject(opIdx, objId);
    if (!imgData) {
      warn("Dependent image isn't ready yet");
      return;
    }
    this.paintInlineImageXObject(opIdx, imgData);
  }
  paintImageXObjectRepeat(opIdx, objId, scaleX, scaleY, positions) {
    if (!this.contentVisible) {
      return;
    }
    const imgData = this.getObject(opIdx, objId);
    if (!imgData) {
      warn("Dependent image isn't ready yet");
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
    this.paintInlineImageXObjectGroup(opIdx, imgData, map);
  }
  applyTransferMapsToCanvas(ctx) {
    if (this.current.transferMaps !== "none") {
      ctx.filter = this.current.transferMaps;
      ctx.drawImage(ctx.canvas, 0, 0);
      ctx.filter = "none";
    } else {
      this.current.transferMapsFallback?.applyToCanvas(ctx);
    }
    return ctx.canvas;
  }
  applyTransferMapsToBitmap(imgData) {
    const {
      transferMaps,
      transferMapsFallback
    } = this.current;
    if (transferMaps === "none" && !transferMapsFallback) {
      return {
        img: imgData.bitmap,
        canvasEntry: null
      };
    }
    const {
      bitmap,
      width,
      height
    } = imgData;
    const tmpCanvas = this.canvasFactory.create(width, height);
    const tmpCtx = tmpCanvas.context;
    tmpCtx.filter = transferMaps;
    tmpCtx.drawImage(bitmap, 0, 0);
    tmpCtx.filter = "none";
    transferMapsFallback?.applyToCanvas(tmpCtx);
    return {
      img: tmpCanvas.canvas,
      canvasEntry: tmpCanvas
    };
  }
  paintInlineImageXObject(opIdx, imgData) {
    if (!this.contentVisible) {
      return;
    }
    const width = imgData.width;
    const height = imgData.height;
    const started = this.#beginKnockoutElement(this.current.fillAlpha);
    const ctx = this.ctx;
    this.save(opIdx);
    const {
      filter
    } = ctx;
    if (filter !== "none" && filter !== "") {
      ctx.filter = "none";
    }
    ctx.scale(1 / width, -1 / height);
    let imgToPaint;
    let inlineImgCanvas = null;
    if (imgData.bitmap) {
      const result = this.applyTransferMapsToBitmap(imgData);
      imgToPaint = result.img;
      inlineImgCanvas = result.canvasEntry;
    } else {
      const tmpCanvas = this.canvasFactory.create(width, height);
      putBinaryImageData(tmpCanvas.context, imgData);
      imgToPaint = this.applyTransferMapsToCanvas(tmpCanvas.context);
      inlineImgCanvas = tmpCanvas;
    }
    const scaled = this._scaleImage(imgToPaint, getCurrentTransformInverse(ctx));
    ctx.imageSmoothingEnabled = getImageSmoothingEnabled(getCurrentTransform(ctx), imgData.interpolate, this.pixelRatio);
    if (this.dependencyTracker) {
      this.dependencyTracker.resetBBox(opIdx).recordBBox(opIdx, ctx, 0, width, -height, 0).recordDependencies(opIdx, Dependencies.imageXObject).recordOperation(opIdx);
      this.imagesTracker?.record(ctx, width, height, this.dependencyTracker.clipBox);
    }
    drawImageAtIntegerCoords(ctx, scaled.img, 0, 0, scaled.paintWidth, scaled.paintHeight, 0, -height, width, height);
    if (scaled.tmpCanvas) {
      this.canvasFactory.destroy(scaled.tmpCanvas);
    }
    if (inlineImgCanvas) {
      this.canvasFactory.destroy(inlineImgCanvas);
    }
    this.compose();
    this.restore(opIdx);
    this.#endKnockoutElement(started);
  }
  paintInlineImageXObjectGroup(opIdx, imgData, map) {
    if (!this.contentVisible) {
      return;
    }
    const started = this.#beginKnockoutElement(this.current.fillAlpha);
    const ctx = this.ctx;
    let imgToPaint;
    let inlineImgCanvas = null;
    if (imgData.bitmap && !this.current.transferMapsFallback) {
      imgToPaint = imgData.bitmap;
    } else if (imgData.bitmap) {
      ({
        img: imgToPaint,
        canvasEntry: inlineImgCanvas
      } = this.applyTransferMapsToBitmap(imgData));
    } else {
      const w = imgData.width;
      const h = imgData.height;
      const tmpCanvas = this.canvasFactory.create(w, h);
      putBinaryImageData(tmpCanvas.context, imgData);
      imgToPaint = this.applyTransferMapsToCanvas(tmpCanvas.context);
      inlineImgCanvas = tmpCanvas;
    }
    this.dependencyTracker?.resetBBox(opIdx);
    for (const entry of map) {
      ctx.save();
      ctx.transform(...entry.transform);
      ctx.scale(1, -1);
      drawImageAtIntegerCoords(ctx, imgToPaint, entry.x, entry.y, entry.w, entry.h, 0, -1, 1, 1);
      this.dependencyTracker?.recordBBox(opIdx, ctx, 0, 1, -1, 0);
      ctx.restore();
    }
    if (inlineImgCanvas) {
      this.canvasFactory.destroy(inlineImgCanvas);
    }
    this.dependencyTracker?.recordOperation(opIdx);
    this.compose();
    this.#endKnockoutElement(started);
  }
  paintSolidColorImageMask(opIdx) {
    if (!this.contentVisible) {
      return;
    }
    const started = this.#beginKnockoutElement(this.current.fillAlpha);
    this.dependencyTracker?.resetBBox(opIdx).recordBBox(opIdx, this.ctx, 0, 1, 0, 1).recordDependencies(opIdx, Dependencies.fill).recordOperation(opIdx);
    this.ctx.fillRect(0, 0, 1, 1);
    this.compose();
    this.#endKnockoutElement(started);
  }
  markPoint(opIdx, tag) {}
  markPointProps(opIdx, tag, properties) {}
  beginMarkedContent(opIdx, tag) {
    this.dependencyTracker?.beginMarkedContent(opIdx);
    this.markedContentStack.push({
      visible: true
    });
  }
  beginMarkedContentProps(opIdx, tag, properties) {
    this.dependencyTracker?.beginMarkedContent(opIdx);
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
  endMarkedContent(opIdx) {
    this.dependencyTracker?.endMarkedContent(opIdx);
    this.markedContentStack.pop();
    this.contentVisible = this.isContentVisible();
  }
  beginCompat(opIdx) {}
  endCompat(opIdx) {}
  consumePath(opIdx, path, clipBox) {
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
          ctx.clip(path, "evenodd");
        } else {
          ctx.clip(path);
        }
      }
      this.pendingClip = null;
      this.dependencyTracker?.bboxToClipBoxDropOperation(opIdx).recordFutureForcedDependency("clipPath", opIdx);
    } else {
      this.dependencyTracker?.recordOperation(opIdx);
    }
    this.current.startNewPathAndClipBox(this.current.clipBox);
  }
  getSinglePixelWidth() {
    const m = getCurrentTransform(this.ctx);
    if (m[1] === 0 && m[2] === 0) {
      return 1 / Math.min(Math.abs(m[0]), Math.abs(m[3]));
    }
    const absDet = Math.abs(m[0] * m[3] - m[2] * m[1]);
    const normX = Math.hypot(m[0], m[2]);
    const normY = Math.hypot(m[1], m[3]);
    return Math.max(normX, normY) / absDet;
  }
  getScaleForStroking() {
    if (this._cachedScaleForStroking[0] === -1) {
      const {
        lineWidth
      } = this.current;
      const {
        a,
        b,
        c,
        d
      } = this.ctx.getTransform();
      let scaleX, scaleY;
      if (b === 0 && c === 0) {
        const normX = Math.abs(a);
        const normY = Math.abs(d);
        if (normX === normY) {
          if (lineWidth === 0) {
            scaleX = scaleY = 1 / normX;
          } else {
            const scaledLineWidth = normX * lineWidth;
            scaleX = scaleY = scaledLineWidth < 1 ? 1 / scaledLineWidth : 1;
          }
        } else if (lineWidth === 0) {
          scaleX = 1 / normX;
          scaleY = 1 / normY;
        } else {
          const scaledXLineWidth = normX * lineWidth;
          const scaledYLineWidth = normY * lineWidth;
          scaleX = scaledXLineWidth < 1 ? 1 / scaledXLineWidth : 1;
          scaleY = scaledYLineWidth < 1 ? 1 / scaledYLineWidth : 1;
        }
      } else {
        const absDet = Math.abs(a * d - b * c);
        const normX = Math.hypot(a, b);
        const normY = Math.hypot(c, d);
        if (lineWidth === 0) {
          scaleX = normY / absDet;
          scaleY = normX / absDet;
        } else {
          const baseArea = lineWidth * absDet;
          scaleX = normY > baseArea ? normY / baseArea : 1;
          scaleY = normX > baseArea ? normX / baseArea : 1;
        }
      }
      this._cachedScaleForStroking[0] = scaleX;
      this._cachedScaleForStroking[1] = scaleY;
    }
    return this._cachedScaleForStroking;
  }
  rescaleAndStroke(path, saveRestore) {
    const {
      ctx,
      current: {
        lineWidth
      }
    } = this;
    const [scaleX, scaleY] = this.getScaleForStroking();
    if (scaleX === scaleY) {
      ctx.lineWidth = (lineWidth || 1) * scaleX;
      ctx.stroke(path);
      return;
    }
    const SCALE_MATRIX = CanvasGraphics.#SCALE_MATRIX ??= new DOMMatrix();
    const dashes = ctx.getLineDash();
    if (saveRestore) {
      ctx.save();
    }
    ctx.scale(scaleX, scaleY);
    SCALE_MATRIX.a = 1 / scaleX;
    SCALE_MATRIX.d = 1 / scaleY;
    const newPath = new Path2D();
    newPath.addPath(path, SCALE_MATRIX);
    if (dashes.length > 0) {
      const scale = Math.max(scaleX, scaleY);
      ctx.setLineDash(dashes.map(x => x / scale));
      ctx.lineDashOffset /= scale;
    }
    ctx.lineWidth = lineWidth || 1;
    ctx.stroke(newPath);
    if (saveRestore) {
      ctx.restore();
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
for (const op in OPS) {
  if (CanvasGraphics.prototype[op] !== undefined) {
    CanvasGraphics.prototype[OPS[op]] = CanvasGraphics.prototype[op];
  }
}

;// ./src/display/dom_canvas_factory.js

class DOMCanvasFactory extends BaseCanvasFactory {
  constructor({
    ownerDocument = globalThis.document,
    enableHWA = false
  }) {
    super({
      enableHWA
    });
    this._document = ownerDocument;
  }
  _createCanvas(width, height) {
    const canvas = this._document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    return canvas;
  }
}

;// ./src/display/dom_filter_factory.js




class DOMFilterFactory extends BaseFilterFactory {
  #baseUrl;
  #_cache;
  #_defs;
  #docId;
  #document;
  #_hcmCache;
  #id = 0;
  constructor({
    docId,
    ownerDocument = globalThis.document
  }) {
    super();
    this.#docId = docId;
    this.#document = ownerDocument;
  }
  get #cache() {
    return this.#_cache ||= new Map();
  }
  get #hcmCache() {
    return this.#_hcmCache ||= new Map();
  }
  get #defs() {
    if (!this.#_defs) {
      const div = this.#document.createElement("div");
      const {
        style
      } = div;
      style.colorScheme = "only light";
      style.visibility = "hidden";
      style.contain = "strict";
      style.width = style.height = 0;
      style.position = "absolute";
      style.top = style.left = 0;
      style.zIndex = -1;
      const svg = this.#document.createElementNS(SVG_NS, "svg");
      svg.setAttribute("width", 0);
      svg.setAttribute("height", 0);
      this.#_defs = this.#document.createElementNS(SVG_NS, "defs");
      div.append(svg);
      svg.append(this.#_defs);
      this.#document.body.append(div);
    }
    return this.#_defs;
  }
  #createTables(maps) {
    const toTable = map => map && Array.from(map, v => v / 255).join(",");
    if (maps.length === 1) {
      const table = toTable(maps[0]);
      return [table, table, table];
    }
    const [mapR, mapG, mapB] = maps;
    return [toTable(mapR), toTable(mapG), toTable(mapB)];
  }
  #createUrl(id) {
    if (this.#baseUrl === undefined) {
      this.#baseUrl = "";
      const url = this.#document.URL;
      if (url !== this.#document.baseURI) {
        if (isDataScheme(url)) {
          warn('#createUrl: ignore "data:"-URL for performance reasons.');
        } else {
          this.#baseUrl = updateUrlHash(url, "");
        }
      }
    }
    return `url(${this.#baseUrl}#${id})`;
  }
  addFilter(maps) {
    if (!maps) {
      return "none";
    }
    let value = this.#cache.get(maps);
    if (value) {
      return value;
    }
    const [tableR, tableG, tableB] = this.#createTables(maps);
    const key = maps.length === 1 ? tableR : `${tableR}${tableG}${tableB}`;
    value = this.#cache.get(key);
    if (value) {
      this.#cache.set(maps, value);
      return value;
    }
    const id = `g_${this.#docId}_transfer_map_${this.#id++}`;
    const url = this.#createUrl(id);
    this.#cache.set(maps, url);
    this.#cache.set(key, url);
    const filter = this.#createFilter(id);
    this.#addTransferMapConversion(tableR, tableG, tableB, filter);
    return url;
  }
  addHCMFilter(fgColor, bgColor) {
    const key = `${fgColor}-${bgColor}`;
    const filterName = "base";
    let info = this.#hcmCache.get(filterName);
    if (info?.key === key) {
      return info.url;
    }
    if (info) {
      info.filter?.remove();
      info.key = key;
      info.url = "none";
      info.filter = null;
    } else {
      info = {
        key,
        url: "none",
        filter: null
      };
      this.#hcmCache.set(filterName, info);
    }
    if (!fgColor || !bgColor) {
      return info.url;
    }
    const fgRGB = this.#getRGB(fgColor);
    fgColor = Util.makeHexColor(...fgRGB);
    const bgRGB = this.#getRGB(bgColor);
    bgColor = Util.makeHexColor(...bgRGB);
    this.#resetDefsColor();
    if (fgColor === "#000000" && bgColor === "#ffffff" || fgColor === bgColor) {
      return info.url;
    }
    const map = Array.from({
      length: 256
    }, (_, i) => computeLuminance(i / 255));
    const table = map.join(",");
    const id = `g_${this.#docId}_hcm_filter`;
    const filter = info.filter = this.#createFilter(id);
    this.#addTransferMapConversion(table, table, table, filter);
    this.#addGrayConversion(filter);
    const getSteps = (c, n) => {
      const start = fgRGB[c] / 255;
      const end = bgRGB[c] / 255;
      const arr = new Array(n + 1);
      for (let i = 0; i <= n; i++) {
        arr[i] = start + i / n * (end - start);
      }
      return arr.join(",");
    };
    this.#addTransferMapConversion(getSteps(0, 5), getSteps(1, 5), getSteps(2, 5), filter);
    info.url = this.#createUrl(id);
    return info.url;
  }
  addSelectionHCMFilter(fgColor, bgColor) {
    return this.addHighlightHCMFilter("selection", fgColor, bgColor, "HighlightText", "Highlight");
  }
  addSelectionFilter() {
    return this.addHighlightHCMFilter("selection_default", "black", "white", "HighlightText", "Highlight");
  }
  createSelectionStyle(pageColors = null) {
    const filter = pageColors ? this.addSelectionHCMFilter(pageColors.foreground, pageColors.background) : this.addSelectionFilter();
    if (filter === "none" || !FeatureTest.platform.isFirefox) {
      return null;
    }
    return {
      "backdrop-filter": filter,
      "background-color": "transparent"
    };
  }
  addAlphaFilter(map) {
    let value = this.#cache.get(map);
    if (value) {
      return value;
    }
    const [tableA] = this.#createTables([map]);
    const key = `alpha_${tableA}`;
    value = this.#cache.get(key);
    if (value) {
      this.#cache.set(map, value);
      return value;
    }
    const id = `g_${this.#docId}_alpha_map_${this.#id++}`;
    const url = this.#createUrl(id);
    this.#cache.set(map, url);
    this.#cache.set(key, url);
    const filter = this.#createFilter(id);
    this.#addTransferMapAlphaConversion(tableA, filter);
    return url;
  }
  addLuminosityFilter(map) {
    let value = this.#cache.get(map || "luminosity");
    if (value) {
      return value;
    }
    let tableA, key;
    if (map) {
      [tableA] = this.#createTables([map]);
      key = `luminosity_${tableA}`;
    } else {
      key = "luminosity";
    }
    value = this.#cache.get(key);
    if (value) {
      this.#cache.set(map, value);
      return value;
    }
    const id = `g_${this.#docId}_luminosity_map_${this.#id++}`;
    const url = this.#createUrl(id);
    this.#cache.set(map, url);
    this.#cache.set(key, url);
    const filter = this.#createFilter(id);
    this.#addLuminosityConversion(filter);
    if (map) {
      this.#addTransferMapAlphaConversion(tableA, filter);
    }
    return url;
  }
  addKnockoutFilter(alpha = 0) {
    const slope = alpha > 0 ? Math.min(1 / alpha, 1e6) : 1e6;
    const key = `knockout_${slope}`;
    const value = this.#cache.get(key);
    if (value) {
      return value;
    }
    const id = `g_${this.#docId}_knockout_filter_${this.#id++}`;
    const url = this.#createUrl(id);
    this.#cache.set(key, url);
    const filter = this.#createFilter(id);
    const feComponentTransfer = this.#document.createElementNS(SVG_NS, "feComponentTransfer");
    filter.append(feComponentTransfer);
    const feFuncA = this.#document.createElementNS(SVG_NS, "feFuncA");
    feFuncA.setAttribute("type", "linear");
    feFuncA.setAttribute("slope", `${slope}`);
    feFuncA.setAttribute("intercept", "0");
    feComponentTransfer.append(feFuncA);
    return url;
  }
  addHighlightHCMFilter(filterName, fgColor, bgColor, newFgColor, newBgColor) {
    const key = `${fgColor}-${bgColor}-${newFgColor}-${newBgColor}`;
    let info = this.#hcmCache.get(filterName);
    if (info?.key === key) {
      return info.url;
    }
    if (info) {
      info.filter?.remove();
      info.key = key;
      info.url = "none";
      info.filter = null;
    } else {
      info = {
        key,
        url: "none",
        filter: null
      };
      this.#hcmCache.set(filterName, info);
    }
    if (!fgColor || !bgColor) {
      return info.url;
    }
    const [fgRGB, bgRGB] = [fgColor, bgColor].map(this.#getRGB.bind(this));
    let fgGray = Math.round(0.2126 * fgRGB[0] + 0.7152 * fgRGB[1] + 0.0722 * fgRGB[2]);
    let bgGray = Math.round(0.2126 * bgRGB[0] + 0.7152 * bgRGB[1] + 0.0722 * bgRGB[2]);
    let [newFgRGB, newBgRGB] = [newFgColor, newBgColor].map(this.#getOpaqueTextColor.bind(this));
    if (bgGray < fgGray) {
      [fgGray, bgGray, newFgRGB, newBgRGB] = [bgGray, fgGray, newBgRGB, newFgRGB];
    }
    this.#resetDefsColor();
    const getSteps = (fg, bg, n) => {
      const arr = new Array(256);
      const step = (bgGray - fgGray) / n;
      const newStart = fg / 255;
      const newStep = (bg - fg) / (255 * n);
      let prev = 0;
      for (let i = 0; i <= n; i++) {
        const k = Math.round(fgGray + i * step);
        const value = newStart + i * newStep;
        for (let j = prev; j <= k; j++) {
          arr[j] = value;
        }
        prev = k + 1;
      }
      for (let i = prev; i < 256; i++) {
        arr[i] = arr[prev - 1];
      }
      return arr.join(",");
    };
    const id = `g_${this.#docId}_hcm_${filterName}_filter`;
    const filter = info.filter = this.#createFilter(id);
    this.#addGrayConversion(filter);
    this.#addTransferMapConversion(getSteps(newFgRGB[0], newBgRGB[0], 5), getSteps(newFgRGB[1], newBgRGB[1], 5), getSteps(newFgRGB[2], newBgRGB[2], 5), filter);
    info.url = this.#createUrl(id);
    return info.url;
  }
  destroy(keepHCM = false) {
    if (keepHCM && this.#_hcmCache?.size) {
      return;
    }
    this.#_defs?.parentNode.parentNode.remove();
    this.#_defs = null;
    this.#_cache?.clear();
    this.#_cache = null;
    this.#_hcmCache?.clear();
    this.#_hcmCache = null;
    this.#id = 0;
  }
  #addLuminosityConversion(filter) {
    const feColorMatrix = this.#document.createElementNS(SVG_NS, "feColorMatrix");
    feColorMatrix.setAttribute("type", "matrix");
    feColorMatrix.setAttribute("values", "0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0.3 0.59 0.11 0 0");
    filter.append(feColorMatrix);
  }
  #addGrayConversion(filter) {
    const feColorMatrix = this.#document.createElementNS(SVG_NS, "feColorMatrix");
    feColorMatrix.setAttribute("type", "matrix");
    feColorMatrix.setAttribute("values", "0.2126 0.7152 0.0722 0 0 0.2126 0.7152 0.0722 0 0 0.2126 0.7152 0.0722 0 0 0 0 0 1 0");
    filter.append(feColorMatrix);
  }
  #createFilter(id) {
    const filter = this.#document.createElementNS(SVG_NS, "filter");
    filter.setAttribute("color-interpolation-filters", "sRGB");
    filter.setAttribute("id", id);
    this.#defs.append(filter);
    return filter;
  }
  #appendFeFunc(feComponentTransfer, func, table) {
    if (!table) {
      return;
    }
    const feFunc = this.#document.createElementNS(SVG_NS, func);
    feFunc.setAttribute("type", "discrete");
    feFunc.setAttribute("tableValues", table);
    feComponentTransfer.append(feFunc);
  }
  #addTransferMapConversion(rTable, gTable, bTable, filter) {
    const feComponentTransfer = this.#document.createElementNS(SVG_NS, "feComponentTransfer");
    filter.append(feComponentTransfer);
    this.#appendFeFunc(feComponentTransfer, "feFuncR", rTable);
    this.#appendFeFunc(feComponentTransfer, "feFuncG", gTable);
    this.#appendFeFunc(feComponentTransfer, "feFuncB", bTable);
  }
  #addTransferMapAlphaConversion(aTable, filter) {
    const feComponentTransfer = this.#document.createElementNS(SVG_NS, "feComponentTransfer");
    filter.append(feComponentTransfer);
    this.#appendFeFunc(feComponentTransfer, "feFuncA", aTable);
  }
  #getRGB(color) {
    this.#defs.style.color = "CanvasText";
    this.#defs.style.backgroundColor = color;
    return getRGB(getComputedStyle(this.#defs).getPropertyValue("background-color"));
  }
  #getRGBA(color) {
    this.#defs.style.color = "CanvasText";
    this.#defs.style.backgroundColor = color;
    return getRGBA(getComputedStyle(this.#defs).getPropertyValue("background-color"));
  }
  #resetDefsColor() {
    this.#defs.style.color = "";
    this.#defs.style.backgroundColor = "";
  }
  #getOpaqueTextColor(color) {
    const [r, g, b, alpha] = this.#getRGBA(color);
    if (alpha === 1) {
      return [r, g, b];
    }
    const [canvasR, canvasG, canvasB] = this.#getRGB("Canvas");
    return [blend(r, canvasR, alpha), blend(g, canvasG, alpha), blend(b, canvasB, alpha)];
  }
}
function blend(fg, bg, alpha) {
  return Math.round(alpha * fg + (1 - alpha) * bg);
}

;// ./src/shared/css_utils.js
const CONTROL_CHAR_REGEXP = /\p{Cc}/u;
function isCSSString(str) {
  const quote = str[0];
  if (str.length < 2 || quote !== `"` && quote !== `'` || str.at(-1) !== quote) {
    return false;
  }
  const end = str.length - 1;
  for (let i = 1; i < end; i++) {
    const char = str[i];
    if (char === quote || CONTROL_CHAR_REGEXP.test(char)) {
      return false;
    }
    if (char === "\\") {
      if (++i >= end || CONTROL_CHAR_REGEXP.test(str[i])) {
        return false;
      }
    }
  }
  return true;
}
function serializeFontFamily(fontFamily) {
  if (isCSSString(fontFamily)) {
    return fontFamily;
  }
  const escaped = fontFamily.replaceAll(/["\\\p{Cc}]/gu, char => char === `"` || char === "\\" ? `\\${char}` : `\\${char.codePointAt(0).toString(16)} `);
  return `"${escaped}"`;
}

;// ./src/display/font_loader.js



class FontLoader {
  #nativeFontFaces = new Set();
  #systemFonts = new Set();
  #styleSheet = null;
  constructor({
    ownerDocument = globalThis.document,
    styleElement = null
  }) {
    this._document = ownerDocument;
    this.styleElement = null;
    this.loadingRequests = [];
    this.loadTestFontId = 0;
  }
  addNativeFontFace(nativeFontFace) {
    this.#nativeFontFaces.add(nativeFontFace);
    this._document.fonts.add(nativeFontFace);
  }
  removeNativeFontFace(nativeFontFace) {
    this.#nativeFontFaces.delete(nativeFontFace);
    this._document.fonts.delete(nativeFontFace);
  }
  insertRule(rule) {
    const styleSheet = this.#getStyleSheet();
    styleSheet.insertRule(rule, styleSheet.cssRules.length);
  }
  #getStyleSheet() {
    if (this.#styleSheet) {
      return this.#styleSheet;
    }
    const StyleSheet = this._document.defaultView?.CSSStyleSheet || globalThis.CSSStyleSheet;
    if (!this.styleElement && StyleSheet) {
      const {
        adoptedStyleSheets
      } = this._document;
      if (adoptedStyleSheets) {
        const styleSheet = new StyleSheet();
        adoptedStyleSheets.push(styleSheet);
        return this.#styleSheet = styleSheet;
      }
    }
    if (!this.styleElement) {
      this.styleElement = this._document.createElement("style");
      this._document.documentElement.getElementsByTagName("head")[0].append(this.styleElement);
    }
    return this.#styleSheet = this.styleElement.sheet;
  }
  clear() {
    for (const nativeFontFace of this.#nativeFontFaces) {
      this._document.fonts.delete(nativeFontFace);
    }
    this.#nativeFontFaces.clear();
    this.#systemFonts.clear();
    if (this.#styleSheet) {
      const {
        adoptedStyleSheets
      } = this._document;
      if (adoptedStyleSheets?.includes(this.#styleSheet)) {
        this._document.adoptedStyleSheets = adoptedStyleSheets.filter(styleSheet => styleSheet !== this.#styleSheet);
      }
      this.#styleSheet = null;
    }
    this.styleElement?.remove();
    this.styleElement = null;
  }
  async loadSystemFont({
    systemFontInfo: info,
    disableFontFace,
    _inspectFont
  }) {
    if (!info || this.#systemFonts.has(info.loadedName)) {
      return;
    }
    assert(!disableFontFace, "loadSystemFont shouldn't be called when `disableFontFace` is set.");
    if (this.isFontLoadingAPISupported) {
      const {
        loadedName,
        src,
        style
      } = info;
      const fontFace = new FontFace(loadedName, src, style);
      this.addNativeFontFace(fontFace);
      try {
        await fontFace.load();
        this.#systemFonts.add(loadedName);
        _inspectFont?.(info);
      } catch {
        warn(`Cannot load system font: ${info.baseFontName}, installing it could help to improve PDF rendering.`);
        this.removeNativeFontFace(fontFace);
      }
      return;
    }
    unreachable("Not implemented: loadSystemFont without the Font Loading API.");
  }
  async bind(font) {
    if (font.attached || font.missingFile && !font.systemFontInfo) {
      return;
    }
    font.attached = true;
    if (font.systemFontInfo) {
      await this.loadSystemFont(font);
      return;
    }
    if (this.isFontLoadingAPISupported) {
      const nativeFontFace = font.createNativeFontFace();
      if (nativeFontFace) {
        this.addNativeFontFace(nativeFontFace);
        try {
          await nativeFontFace.loaded;
        } catch (ex) {
          warn(`Failed to load font '${nativeFontFace.family}': '${ex}'.`);
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
      await this.#testFontLoaded(font);
    }
  }
  get isFontLoadingAPISupported() {
    return shadow(this, "isFontLoadingAPISupported", !!this._document?.fonts);
  }
  get isSyncFontLoadingSupported() {
    return shadow(this, "isSyncFontLoadingSupported", isNodeJS || FeatureTest.platform.isFirefox);
  }
  #testFontLoaded(font) {
    function completeRequest() {
      assert(!request.done, "completeRequest() cannot be called twice.");
      request.done = true;
      while (loadingRequests.length > 0 && loadingRequests[0].done) {
        const otherRequest = loadingRequests.shift();
        setTimeout(otherRequest.resolve, 0);
      }
    }
    const {
      loadingRequests
    } = this;
    const {
      promise,
      resolve
    } = Promise.withResolvers();
    const request = {
      done: false,
      resolve
    };
    loadingRequests.push(request);
    this._loadTestFont ??= atob("T1RUTwALAIAAAwAwQ0ZGIDHtZg4AAAOYAAAAgUZGVE1lkzZwAAAEHAAAABxHREVGABQA" + "FQAABDgAAAAeT1MvMlYNYwkAAAEgAAAAYGNtYXABDQLUAAACNAAAAUJoZWFk/xVFDQAA" + "ALwAAAA2aGhlYQdkA+oAAAD0AAAAJGhtdHgD6AAAAAAEWAAAAAZtYXhwAAJQAAAAARgA" + "AAAGbmFtZVjmdH4AAAGAAAAAsXBvc3T/hgAzAAADeAAAACAAAQAAAAEAALZRFsRfDzz1" + "AAsD6AAAAADOBOTLAAAAAM4KHDwAAAAAA+gDIQAAAAgAAgAAAAAAAAABAAADIQAAAFoD" + "6AAAAAAD6AABAAAAAAAAAAAAAAAAAAAAAQAAUAAAAgAAAAQD6AH0AAUAAAKKArwAAACM" + "AooCvAAAAeAAMQECAAACAAYJAAAAAAAAAAAAAQAAAAAAAAAAAAAAAFBmRWQAwAAuAC4D" + "IP84AFoDIQAAAAAAAQAAAAAAAAAAACAAIAABAAAADgCuAAEAAAAAAAAAAQAAAAEAAAAA" + "AAEAAQAAAAEAAAAAAAIAAQAAAAEAAAAAAAMAAQAAAAEAAAAAAAQAAQAAAAEAAAAAAAUA" + "AQAAAAEAAAAAAAYAAQAAAAMAAQQJAAAAAgABAAMAAQQJAAEAAgABAAMAAQQJAAIAAgAB" + "AAMAAQQJAAMAAgABAAMAAQQJAAQAAgABAAMAAQQJAAUAAgABAAMAAQQJAAYAAgABWABY" + "AAAAAAAAAwAAAAMAAAAcAAEAAAAAADwAAwABAAAAHAAEACAAAAAEAAQAAQAAAC7//wAA" + "AC7////TAAEAAAAAAAABBgAAAQAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" + "AAAAAAAAAAAAAAAAAAEAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA" + "AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMAAAAAAAD/gwAyAAAAAQAAAAAAAAAAAAAAAAAA" + "AAABAAQEAAEBAQJYAAEBASH4DwD4GwHEAvgcA/gXBIwMAYuL+nz5tQXkD5j3CBLnEQAC" + "AQEBIVhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYAAABAQAADwACAQEEE/t3" + "Dov6fAH6fAT+fPp8+nwHDosMCvm1Cvm1DAz6fBQAAAAAAAABAAAAAMmJbzEAAAAAzgTj" + "FQAAAADOBOQpAAEAAAAAAAAADAAUAAQAAAABAAAAAgABAAAAAAAAAAAD6AAAAAAAAA==");
    function int32(data, offset) {
      return data.charCodeAt(offset) << 24 | data.charCodeAt(offset + 1) << 16 | data.charCodeAt(offset + 2) << 8 | data.charCodeAt(offset + 3) & 0xff;
    }
    function string32(value) {
      return String.fromCharCode(value >> 24 & 0xff, value >> 16 & 0xff, value >> 8 & 0xff, value & 0xff);
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
      if (++called > 30) {
        warn("Load test font never loaded.");
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
    data = spliceString(data, CFF_CHECKSUM_OFFSET, 4, string32(checksum));
    const url = `url(data:font/opentype;base64,${btoa(data)});`;
    const rule = `@font-face {font-family:"${loadTestFontId}";src:${url}}`;
    this.insertRule(rule);
    const div = this._document.createElement("div");
    div.style.visibility = "hidden";
    div.style.width = div.style.height = "10px";
    div.style.position = "absolute";
    div.style.top = div.style.left = "0px";
    for (const name of [font.loadedName, loadTestFontId]) {
      const span = this._document.createElement("span");
      span.textContent = "Hi";
      span.style.fontFamily = name;
      div.append(span);
    }
    this._document.body.append(div);
    isFontReady(loadTestFontId, () => {
      div.remove();
      completeRequest();
    });
    return promise;
  }
}
class FontFaceObject {
  #compiledPaths = new Map();
  #fontData;
  constructor(translatedData, inspectFont = null, charProcOperatorList, extra) {
    this.#fontData = translatedData;
    this._inspectFont = inspectFont;
    if (charProcOperatorList) {
      this.charProcOperatorList = charProcOperatorList;
    }
    if (extra) {
      Object.assign(this, extra);
    }
  }
  createNativeFontFace() {
    const {
      data
    } = this;
    if (!data || this.disableFontFace) {
      return null;
    }
    let nativeFontFace;
    if (!this.cssFontInfo) {
      nativeFontFace = new FontFace(this.loadedName, data, {});
    } else {
      const css = {
        weight: this.cssFontInfo.fontWeight
      };
      if (this.cssFontInfo.italicAngle) {
        css.style = `oblique ${this.cssFontInfo.italicAngle}deg`;
      }
      nativeFontFace = new FontFace(serializeFontFamily(this.cssFontInfo.fontFamily), data, css);
    }
    this._inspectFont?.(this);
    return nativeFontFace;
  }
  createFontFaceRule() {
    const {
      data
    } = this;
    if (!data || this.disableFontFace) {
      return null;
    }
    const url = `url(data:${this.mimetype};base64,${data.toBase64()});`;
    let rule;
    if (!this.cssFontInfo) {
      rule = `@font-face {font-family:"${this.loadedName}";src:${url}}`;
    } else {
      let css = `font-weight: ${this.cssFontInfo.fontWeight};`;
      if (this.cssFontInfo.italicAngle) {
        css += `font-style: oblique ${this.cssFontInfo.italicAngle}deg;`;
      }
      const fontFamily = serializeFontFamily(this.cssFontInfo.fontFamily);
      rule = `@font-face {font-family:${fontFamily};${css}src:${url}}`;
    }
    this._inspectFont?.(this, url);
    return rule;
  }
  getPathGenerator(objs, character) {
    let path = this.#compiledPaths.get(character);
    if (path) {
      return path;
    }
    const objId = `${this.loadedName}_path_${character}`;
    let cmds;
    try {
      cmds = objs.get(objId);
    } catch (ex) {
      warn(`getPathGenerator - ignoring character: "${ex}".`);
    }
    path = makePathFromDrawOPS(cmds?.path);
    if (!this.fontExtraProperties) {
      objs.delete(objId);
    }
    this.#compiledPaths.set(character, path);
    return path;
  }
  get black() {
    return this.#fontData.black;
  }
  get bold() {
    return this.#fontData.bold;
  }
  get disableFontFace() {
    return this.#fontData.disableFontFace;
  }
  set disableFontFace(value) {
    shadow(this, "disableFontFace", !!value);
  }
  get fontExtraProperties() {
    return this.#fontData.fontExtraProperties;
  }
  get isInvalidPDFjsFont() {
    return this.#fontData.isInvalidPDFjsFont;
  }
  get isType3Font() {
    return this.#fontData.isType3Font;
  }
  get italic() {
    return this.#fontData.italic;
  }
  get missingFile() {
    return this.#fontData.missingFile;
  }
  get remeasure() {
    return this.#fontData.remeasure;
  }
  get vertical() {
    return this.#fontData.vertical;
  }
  get bbox() {
    return this.#fontData.bbox;
  }
  get fontMatrix() {
    return this.#fontData.fontMatrix;
  }
  get fallbackName() {
    return this.#fontData.fallbackName;
  }
  get loadedName() {
    return this.#fontData.loadedName;
  }
  get mimetype() {
    return this.missingFile ? null : "font/opentype";
  }
  get data() {
    return this.#fontData.data;
  }
  clearData() {
    this.#fontData.clearData();
  }
  get cssFontInfo() {
    return this.#fontData.cssFontInfo;
  }
  get systemFontInfo() {
    return this.#fontData.systemFontInfo;
  }
}

;// ./src/shared/base_pdf_stream.js

class BasePDFStream {
  #PDFStreamReader = null;
  #PDFStreamRangeReader = null;
  _fullReader = null;
  _rangeReaders = new Set();
  _source = null;
  constructor(source, PDFStreamReader, PDFStreamRangeReader) {
    this._source = source;
    this.#PDFStreamReader = PDFStreamReader;
    this.#PDFStreamRangeReader = PDFStreamRangeReader;
  }
  get _progressiveDataLength() {
    return this._fullReader?._loaded ?? 0;
  }
  getFullReader() {
    assert(!this._fullReader, "BasePDFStream.getFullReader can only be called once.");
    return this._fullReader = new this.#PDFStreamReader(this);
  }
  getRangeReader(begin, end) {
    if (end <= this._progressiveDataLength) {
      return null;
    }
    const reader = new this.#PDFStreamRangeReader(this, begin, end);
    this._rangeReaders.add(reader);
    return reader;
  }
  cancelAllRequests(reason) {
    this._fullReader?.cancel(reason);
    for (const reader of new Set(this._rangeReaders)) {
      reader.cancel(reason);
    }
  }
}
class BasePDFStreamReader {
  onProgress = null;
  _contentLength = 0;
  _filename = null;
  _headersCapability = Promise.withResolvers();
  _isRangeSupported = false;
  _isStreamingSupported = false;
  _loaded = 0;
  _stream = null;
  constructor(stream) {
    this._stream = stream;
  }
  _callOnProgress() {
    this.onProgress?.({
      loaded: this._loaded,
      total: this._contentLength
    });
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
    unreachable("Abstract method `read` called");
  }
  cancel(reason) {
    unreachable("Abstract method `cancel` called");
  }
}
class BasePDFStreamRangeReader {
  _stream = null;
  constructor(stream, begin, end) {
    this._stream = stream;
  }
  async read() {
    unreachable("Abstract method `read` called");
  }
  cancel(reason) {
    unreachable("Abstract method `cancel` called");
  }
}

;// ./src/display/content_disposition.js

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
        const buffer = stringToBytes(value);
        value = decoder.decode(buffer);
        needsEncodingFixup = false;
      } catch {}
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
        parts[i] = parts[i].replaceAll(/\\(.)/g, "$1");
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
    return value.replaceAll(/=\?([\w-]*)\?([QB])\?((?:[^?]|\?(?!=))*)\?=/gi, function (matches, charset, encoding, text) {
      if (encoding === "q" || encoding === "Q") {
        text = text.replaceAll("_", " ").replaceAll(/=([0-9a-f]{2})/gi, (_, hex) => String.fromCharCode(parseInt(hex, 16)));
        return textdecode(charset, text);
      }
      try {
        text = atob(text);
      } catch {}
      return textdecode(charset, text);
    });
  }
  return "";
}

;// ./src/display/network_utils.js



function createHeaders(isHttp, httpHeaders) {
  const headers = new Headers();
  if (!isHttp || !httpHeaders || typeof httpHeaders !== "object") {
    return headers;
  }
  for (const key in httpHeaders) {
    const val = httpHeaders[key];
    if (val !== undefined) {
      headers.append(key, val);
    }
  }
  return headers;
}
function trimHeadersEnd(str) {
  let end = str.length;
  while (end > 0 && str[end - 1] !== " " && /\s/.test(str[end - 1])) {
    end--;
  }
  return str.slice(0, end);
}
function getResponseOrigin(url) {
  return URL.parse(url)?.origin ?? null;
}
function validateRangeRequestCapabilities({
  responseHeaders,
  isHttp,
  rangeChunkSize,
  disableRange
}) {
  const rv = {
    contentLength: 0,
    isRangeSupported: false
  };
  const length = parseInt(responseHeaders.get("Content-Length"), 10);
  if (!Number.isInteger(length)) {
    return rv;
  }
  rv.contentLength = length;
  if (length <= 2 * rangeChunkSize) {
    return rv;
  }
  if (disableRange || !isHttp || responseHeaders.get("Accept-Ranges") !== "bytes") {
    return rv;
  }
  const contentEncoding = responseHeaders.get("Content-Encoding") || "identity";
  if (contentEncoding === "identity") {
    rv.isRangeSupported = true;
  }
  return rv;
}
function extractFilenameFromHeader(responseHeaders) {
  const contentDisposition = responseHeaders.get("Content-Disposition");
  if (contentDisposition) {
    let filename = getFilenameFromContentDispositionHeader(contentDisposition);
    if (filename.includes("%")) {
      try {
        filename = decodeURIComponent(filename);
      } catch {}
    }
    if (isPdfFile(filename)) {
      return filename;
    }
  }
  return null;
}
function createResponseError(status, url) {
  return new ResponseException(`Unexpected server response (${status}) while retrieving PDF "${url.href}".`, status, status === 404 || status === 0 && url.protocol === "file:");
}
function ensureResponseOrigin(rangeOrigin, origin) {
  if (rangeOrigin !== origin) {
    throw new Error(`Expected range response-origin "${rangeOrigin}" to match "${origin}".`);
  }
}

;// ./src/display/fetch_stream.js



function fetchUrl(url, headers, withCredentials, abortController) {
  return fetch(url, {
    method: "GET",
    headers,
    signal: abortController.signal,
    mode: "cors",
    credentials: withCredentials ? "include" : "same-origin",
    redirect: "follow"
  });
}
function ensureResponseStatus(status, url) {
  if (status !== 200 && status !== 206) {
    throw createResponseError(status, url);
  }
}
function getArrayBuffer(val) {
  if (val instanceof Uint8Array) {
    return val.buffer;
  }
  if (val instanceof ArrayBuffer) {
    return val;
  }
  throw new Error(`getArrayBuffer - unexpected data: ${val}`);
}
class PDFFetchStream extends BasePDFStream {
  _responseOrigin = null;
  constructor(source) {
    super(source, PDFFetchStreamReader, PDFFetchStreamRangeReader);
    const {
      httpHeaders,
      url
    } = source;
    assert(/https?:/.test(url.protocol), "PDFFetchStream only supports http(s):// URLs.");
    this.headers = createHeaders(true, httpHeaders);
  }
}
class PDFFetchStreamReader extends BasePDFStreamReader {
  _abortController = new AbortController();
  _reader = null;
  constructor(stream) {
    super(stream);
    const {
      disableRange,
      disableStream,
      rangeChunkSize,
      url,
      withCredentials
    } = stream._source;
    this._isStreamingSupported = !disableStream;
    const headers = new Headers(stream.headers);
    fetchUrl(url, headers, withCredentials, this._abortController).then(response => {
      stream._responseOrigin = getResponseOrigin(response.url);
      ensureResponseStatus(response.status, url);
      this._reader = response.body.getReader();
      const responseHeaders = response.headers;
      const {
        contentLength,
        isRangeSupported
      } = validateRangeRequestCapabilities({
        responseHeaders,
        isHttp: true,
        rangeChunkSize,
        disableRange
      });
      this._contentLength = contentLength;
      this._isRangeSupported = isRangeSupported;
      this._filename = extractFilenameFromHeader(responseHeaders);
      if (!this._isStreamingSupported && this._isRangeSupported) {
        this.cancel(new AbortException("Streaming is disabled."));
      }
      this._headersCapability.resolve();
    }).catch(this._headersCapability.reject);
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
    this._callOnProgress();
    return {
      value: getArrayBuffer(value),
      done: false
    };
  }
  cancel(reason) {
    this._reader?.cancel(reason).catch(() => {});
    this._abortController.abort();
  }
}
class PDFFetchStreamRangeReader extends BasePDFStreamRangeReader {
  _abortController = new AbortController();
  _readCapability = Promise.withResolvers();
  _reader = null;
  constructor(stream, begin, end) {
    super(stream, begin, end);
    const {
      url,
      withCredentials
    } = stream._source;
    const headers = new Headers(stream.headers);
    headers.append("Range", `bytes=${begin}-${end - 1}`);
    fetchUrl(url, headers, withCredentials, this._abortController).then(response => {
      const responseOrigin = getResponseOrigin(response.url);
      ensureResponseOrigin(responseOrigin, stream._responseOrigin);
      ensureResponseStatus(response.status, url);
      this._reader = response.body.getReader();
      this._readCapability.resolve();
    }).catch(this._readCapability.reject);
    this._readCapability.promise.catch(() => {});
  }
  async read() {
    await this._readCapability.promise;
    const {
      value,
      done
    } = await this._reader.read();
    return done ? {
      value,
      done
    } : {
      value: getArrayBuffer(value),
      done: false
    };
  }
  cancel(reason) {
    this._reader?.cancel(reason).catch(() => {});
    this._abortController.abort();
  }
}

;// ./src/display/transport_stream.js



function transport_stream_getArrayBuffer(val) {
  return val instanceof Uint8Array && val.byteLength === val.buffer.byteLength ? val.buffer : new Uint8Array(val).buffer;
}
function endRequests() {
  for (const capability of this._requests) {
    capability.resolve({
      value: undefined,
      done: true
    });
  }
  this._requests.length = 0;
}
class PDFDataTransportStream extends BasePDFStream {
  _progressiveDone = false;
  _queuedChunks = [];
  constructor(source) {
    super(source, PDFDataTransportStreamReader, PDFDataTransportStreamRangeReader);
    const {
      pdfDataRangeTransport
    } = source;
    const {
      initialData,
      progressiveDone
    } = pdfDataRangeTransport;
    if (initialData?.length > 0) {
      const buffer = transport_stream_getArrayBuffer(initialData);
      this._queuedChunks.push(buffer);
    }
    this._progressiveDone = progressiveDone;
    const listener = args => {
      switch (args.type) {
        case "range":
        case "progressiveRead":
          this.#onReceiveData(args.begin, args.chunk);
          break;
        case "progressiveDone":
          this._fullReader?.progressiveDone();
          this._progressiveDone = true;
          break;
      }
    };
    pdfDataRangeTransport.transportReady(listener);
  }
  #onReceiveData(begin, chunk) {
    const buffer = transport_stream_getArrayBuffer(chunk);
    if (begin === undefined) {
      if (this._fullReader) {
        this._fullReader._enqueue(buffer);
      } else {
        this._queuedChunks.push(buffer);
      }
    } else {
      const rangeReader = this._rangeReaders.keys().find(r => r._begin === begin);
      assert(rangeReader, "#onReceiveData - no `PDFDataTransportStreamRangeReader` instance found.");
      rangeReader._enqueue(buffer);
    }
  }
  getFullReader() {
    const reader = super.getFullReader();
    this._queuedChunks = null;
    return reader;
  }
  getRangeReader(begin, end) {
    const reader = super.getRangeReader(begin, end);
    if (reader) {
      reader.onDone = () => this._rangeReaders.delete(reader);
      this._source.pdfDataRangeTransport.requestDataRange(begin, end);
    }
    return reader;
  }
  cancelAllRequests(reason) {
    super.cancelAllRequests(reason);
    this._source.pdfDataRangeTransport.abort();
  }
}
class PDFDataTransportStreamReader extends BasePDFStreamReader {
  #endRequests = endRequests.bind(this);
  _done = false;
  _queuedChunks = null;
  _requests = [];
  constructor(stream) {
    super(stream);
    const {
      pdfDataRangeTransport,
      disableRange,
      disableStream
    } = stream._source;
    const {
      length,
      contentDispositionFilename
    } = pdfDataRangeTransport;
    this._queuedChunks = stream._queuedChunks || [];
    for (const chunk of this._queuedChunks) {
      this._loaded += chunk.byteLength;
    }
    this._done = stream._progressiveDone;
    this._contentLength = length;
    this._isStreamingSupported = !disableStream;
    this._isRangeSupported = !disableRange;
    if (isPdfFile(contentDispositionFilename)) {
      this._filename = contentDispositionFilename;
    }
    this._headersCapability.resolve();
    const loaded = this._loaded;
    Promise.resolve().then(() => {
      if (loaded > 0 && this._loaded === loaded) {
        this._callOnProgress();
      }
    });
  }
  _enqueue(chunk) {
    if (this._done) {
      return;
    }
    if (this._requests.length > 0) {
      const capability = this._requests.shift();
      capability.resolve({
        value: chunk,
        done: false
      });
    } else {
      this._queuedChunks.push(chunk);
    }
    this._loaded += chunk.byteLength;
    this._callOnProgress();
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
    const capability = Promise.withResolvers();
    this._requests.push(capability);
    return capability.promise;
  }
  cancel(reason) {
    this._done = true;
    this.#endRequests();
  }
  progressiveDone() {
    this._done ||= true;
    if (this._queuedChunks.length === 0) {
      this.#endRequests();
    }
  }
}
class PDFDataTransportStreamRangeReader extends BasePDFStreamRangeReader {
  #endRequests = endRequests.bind(this);
  onDone = null;
  _begin = -1;
  _done = false;
  _queuedChunk = null;
  _requests = [];
  constructor(stream, begin, end) {
    super(stream, begin, end);
    this._begin = begin;
  }
  _enqueue(chunk) {
    if (this._done) {
      return;
    }
    if (this._requests.length === 0) {
      this._queuedChunk = chunk;
    } else {
      const capability = this._requests.shift();
      capability.resolve({
        value: chunk,
        done: false
      });
      this.#endRequests();
    }
    this._done = true;
    this.onDone?.();
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
    const capability = Promise.withResolvers();
    this._requests.push(capability);
    return capability.promise;
  }
  cancel(reason) {
    this._done = true;
    this.#endRequests();
    this.onDone?.();
  }
}

;// ./src/display/network.js




const OK_RESPONSE = 200;
const PARTIAL_CONTENT_RESPONSE = 206;
function network_getArrayBuffer(val) {
  return typeof val !== "string" ? val : stringToBytes(val).buffer;
}
class PDFNetworkStream extends BasePDFStream {
  #pendingRequests = new WeakMap();
  _responseOrigin = null;
  constructor(source) {
    super(source, PDFNetworkStreamReader, PDFNetworkStreamRangeReader);
    const {
      httpHeaders,
      url
    } = source;
    this.url = url;
    this.isHttp = /https?:/.test(url.protocol);
    this.headers = createHeaders(this.isHttp, httpHeaders);
  }
  _request(args) {
    const xhr = new XMLHttpRequest();
    const pendingRequest = {
      validateStatus: null,
      onHeadersReceived: args.onHeadersReceived,
      onDone: args.onDone,
      onError: args.onError,
      onProgress: args.onProgress
    };
    this.#pendingRequests.set(xhr, pendingRequest);
    xhr.open("GET", this.url);
    xhr.withCredentials = this._source.withCredentials;
    for (const [key, val] of this.headers) {
      xhr.setRequestHeader(key, val);
    }
    if (this.isHttp && "begin" in args && "end" in args) {
      xhr.setRequestHeader("Range", `bytes=${args.begin}-${args.end - 1}`);
      pendingRequest.validateStatus = status => status === PARTIAL_CONTENT_RESPONSE || status === OK_RESPONSE;
    } else {
      pendingRequest.validateStatus = status => status === OK_RESPONSE;
    }
    xhr.responseType = "arraybuffer";
    assert(args.onError, "Expected `onError` callback to be provided.");
    xhr.onerror = () => args.onError(xhr.status);
    xhr.onreadystatechange = this.#onStateChange.bind(this, xhr);
    xhr.onprogress = this.#onProgress.bind(this, xhr);
    xhr.send(null);
    return xhr;
  }
  #onProgress(xhr, evt) {
    const pendingRequest = this.#pendingRequests.get(xhr);
    pendingRequest?.onProgress?.(evt);
  }
  #onStateChange(xhr, evt) {
    const pendingRequest = this.#pendingRequests.get(xhr);
    if (!pendingRequest) {
      return;
    }
    if (xhr.readyState >= 2 && pendingRequest.onHeadersReceived) {
      pendingRequest.onHeadersReceived();
      delete pendingRequest.onHeadersReceived;
    }
    if (xhr.readyState !== 4) {
      return;
    }
    if (!this.#pendingRequests.has(xhr)) {
      return;
    }
    this.#pendingRequests.delete(xhr);
    if (xhr.status === 0 && this.isHttp) {
      pendingRequest.onError(xhr.status);
      return;
    }
    const xhrStatus = xhr.status || OK_RESPONSE;
    if (!pendingRequest.validateStatus(xhrStatus)) {
      pendingRequest.onError(xhr.status);
      return;
    }
    const chunk = network_getArrayBuffer(xhr.response);
    if (xhrStatus === PARTIAL_CONTENT_RESPONSE) {
      const rangeHeader = xhr.getResponseHeader("Content-Range");
      if (/bytes \d+-\d+\/\d+/.test(rangeHeader)) {
        pendingRequest.onDone(chunk);
      } else {
        warn(`Missing or invalid "Content-Range" header.`);
        pendingRequest.onError(0);
      }
    } else if (chunk) {
      pendingRequest.onDone(chunk);
    } else {
      pendingRequest.onError(xhr.status);
    }
  }
  _abortRequest(xhr) {
    if (this.#pendingRequests.has(xhr)) {
      this.#pendingRequests.delete(xhr);
      xhr.abort();
    }
  }
  getRangeReader(begin, end) {
    const reader = super.getRangeReader(begin, end);
    if (reader) {
      reader.onClosed = () => this._rangeReaders.delete(reader);
    }
    return reader;
  }
}
class PDFNetworkStreamReader extends BasePDFStreamReader {
  #endRequests = endRequests.bind(this);
  _cachedChunks = [];
  _done = false;
  _requests = [];
  _storedError = null;
  constructor(stream) {
    super(stream);
    this._fullRequestXhr = stream._request({
      onHeadersReceived: this.#onHeadersReceived.bind(this),
      onDone: this.#onDone.bind(this),
      onError: this.#onError.bind(this),
      onProgress: this.#onProgress.bind(this)
    });
  }
  #onHeadersReceived() {
    const stream = this._stream;
    const {
      disableRange,
      rangeChunkSize
    } = stream._source;
    const fullRequestXhr = this._fullRequestXhr;
    stream._responseOrigin = getResponseOrigin(fullRequestXhr.responseURL);
    const rawResponseHeaders = fullRequestXhr.getAllResponseHeaders();
    const responseHeaders = new Headers(rawResponseHeaders ? trimHeadersEnd(rawResponseHeaders.trimStart()).split(/[\r\n]+/).map(x => {
      const [key, ...val] = x.split(": ");
      return [key, val.join(": ")];
    }) : []);
    const {
      contentLength,
      isRangeSupported
    } = validateRangeRequestCapabilities({
      responseHeaders,
      isHttp: stream.isHttp,
      rangeChunkSize,
      disableRange
    });
    this._contentLength = contentLength;
    this._isRangeSupported = isRangeSupported;
    this._filename = extractFilenameFromHeader(responseHeaders);
    if (this._isRangeSupported) {
      stream._abortRequest(fullRequestXhr);
    }
    this._headersCapability.resolve();
  }
  #onDone(chunk) {
    if (this._requests.length > 0) {
      const capability = this._requests.shift();
      capability.resolve({
        value: chunk,
        done: false
      });
    } else {
      this._cachedChunks.push(chunk);
    }
    this._done = true;
    if (this._cachedChunks.length === 0) {
      this.#endRequests();
    }
  }
  #onError(status) {
    this._storedError = createResponseError(status, this._stream.url);
    this._headersCapability.reject(this._storedError);
    for (const capability of this._requests) {
      capability.reject(this._storedError);
    }
    this._requests.length = 0;
    this._cachedChunks.length = 0;
  }
  #onProgress(evt) {
    this.onProgress?.({
      loaded: evt.loaded,
      total: evt.lengthComputable ? evt.total : this._contentLength
    });
  }
  async read() {
    await this._headersCapability.promise;
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
    const capability = Promise.withResolvers();
    this._requests.push(capability);
    return capability.promise;
  }
  cancel(reason) {
    this._done = true;
    this._headersCapability.reject(reason);
    this.#endRequests();
    this._stream._abortRequest(this._fullRequestXhr);
    this._fullRequestXhr = null;
  }
}
class PDFNetworkStreamRangeReader extends BasePDFStreamRangeReader {
  #endRequests = endRequests.bind(this);
  onClosed = null;
  _done = false;
  _queuedChunk = null;
  _requests = [];
  _storedError = null;
  constructor(stream, begin, end) {
    super(stream, begin, end);
    this._requestXhr = stream._request({
      begin,
      end,
      onHeadersReceived: this.#onHeadersReceived.bind(this),
      onDone: this.#onDone.bind(this),
      onError: this.#onError.bind(this),
      onProgress: null
    });
  }
  #onHeadersReceived() {
    const responseOrigin = getResponseOrigin(this._requestXhr?.responseURL);
    try {
      ensureResponseOrigin(responseOrigin, this._stream._responseOrigin);
    } catch (ex) {
      this._storedError = ex;
      this.#onError(0);
    }
  }
  #onDone(chunk) {
    if (this._requests.length > 0) {
      const capability = this._requests.shift();
      capability.resolve({
        value: chunk,
        done: false
      });
    } else {
      this._queuedChunk = chunk;
    }
    this._done = true;
    this.#endRequests();
    this.onClosed?.();
  }
  #onError(status) {
    this._storedError ??= createResponseError(status, this._stream.url);
    for (const capability of this._requests) {
      capability.reject(this._storedError);
    }
    this._requests.length = 0;
    this._queuedChunk = null;
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
    const capability = Promise.withResolvers();
    this._requests.push(capability);
    return capability.promise;
  }
  cancel(reason) {
    this._done = true;
    this.#endRequests();
    this._stream._abortRequest(this._requestXhr);
    this.onClosed?.();
  }
}

;// ./src/display/node_stream.js




function getReadableStream(url, opts = null) {
  const fs = process.getBuiltinModule("fs");
  const {
    Readable
  } = process.getBuiltinModule("stream");
  const readStream = fs.createReadStream(url, opts);
  return Readable.toWeb(readStream);
}
class PDFNodeStream extends BasePDFStream {
  constructor(source) {
    super(source, PDFNodeStreamReader, PDFNodeStreamRangeReader);
    const {
      url
    } = source;
    assert(url.protocol === "file:", "PDFNodeStream only supports file:// URLs.");
  }
}
class PDFNodeStreamReader extends BasePDFStreamReader {
  _reader = null;
  constructor(stream) {
    super(stream);
    const {
      disableRange,
      disableStream,
      rangeChunkSize,
      url
    } = stream._source;
    this._isStreamingSupported = !disableStream;
    const fs = process.getBuiltinModule("fs/promises");
    fs.lstat(url).then(stat => {
      const readableStream = getReadableStream(url);
      this._reader = readableStream.getReader();
      const {
        size
      } = stat;
      this._contentLength = size;
      this._isRangeSupported = !disableRange && size > 2 * rangeChunkSize;
      if (!this._isStreamingSupported && this._isRangeSupported) {
        this.cancel(new AbortException("Streaming is disabled."));
      }
      this._headersCapability.resolve();
    }).catch(error => {
      if (error.code === "ENOENT") {
        error = createResponseError(0, url);
      }
      this._headersCapability.reject(error);
    });
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
    this._callOnProgress();
    return {
      value: getArrayBuffer(value),
      done: false
    };
  }
  cancel(reason) {
    this._reader?.cancel(reason).catch(() => {});
  }
}
class PDFNodeStreamRangeReader extends BasePDFStreamRangeReader {
  _readCapability = Promise.withResolvers();
  _reader = null;
  constructor(stream, begin, end) {
    super(stream, begin, end);
    const {
      url
    } = stream._source;
    try {
      const readableStream = getReadableStream(url, {
        start: begin,
        end: end - 1
      });
      this._reader = readableStream.getReader();
      this._readCapability.resolve();
    } catch (error) {
      this._readCapability.reject(error);
    }
    this._readCapability.promise.catch(() => {});
  }
  async read() {
    await this._readCapability.promise;
    const {
      value,
      done
    } = await this._reader.read();
    return done ? {
      value,
      done
    } : {
      value: getArrayBuffer(value),
      done: false
    };
  }
  cancel(reason) {
    this._reader?.cancel(reason).catch(() => {});
  }
}

;// ./src/display/network_stream.js





function getNetworkStream(url) {
  return isValidFetchUrl(url) ? PDFFetchStream : isNodeJS ? PDFNodeStream : PDFNetworkStream;
}

;// ./src/display/worker_options.js
class GlobalWorkerOptions {
  static #port = null;
  static #rendererPorts = [];
  static #rendererSrc = "";
  static #src = "";
  static get rendererPorts() {
    return this.#rendererPorts;
  }
  static set rendererPorts(val) {
    if (!Array.isArray(val) || !val.every(port => typeof Worker !== "undefined" && port instanceof Worker)) {
      throw new Error("Invalid `rendererPorts` type.");
    }
    this.#rendererPorts = val;
  }
  static get rendererSrc() {
    return this.#rendererSrc;
  }
  static set rendererSrc(val) {
    if (typeof val !== "string") {
      throw new Error("Invalid `rendererSrc` type.");
    }
    this.#rendererSrc = val;
  }
  static get workerPort() {
    return this.#port;
  }
  static set workerPort(val) {
    if (!(typeof Worker !== "undefined" && val instanceof Worker) && val !== null) {
      throw new Error("Invalid `workerPort` type.");
    }
    this.#port = val;
  }
  static get workerSrc() {
    return this.#src;
  }
  static set workerSrc(val) {
    if (typeof val !== "string") {
      throw new Error("Invalid `workerSrc` type.");
    }
    this.#src = val;
  }
}

;// ./src/display/metadata.js
class Metadata {
  #map;
  #data;
  constructor({
    parsedData,
    rawData
  }) {
    this.#map = parsedData;
    this.#data = rawData;
  }
  getRaw() {
    return this.#data;
  }
  get(name) {
    return this.#map.get(name) ?? null;
  }
  [Symbol.iterator]() {
    return this.#map.entries();
  }
}

;// ./src/shared/obj_bin_transform_utils.js

class CSS_FONT_INFO {
  static strings = ["fontFamily", "fontWeight", "italicAngle"];
}
class SYSTEM_FONT_INFO {
  static strings = ["css", "loadedName", "baseFontName", "src"];
}
class FONT_INFO {
  static bools = ["black", "bold", "disableFontFace", "fontExtraProperties", "isInvalidPDFjsFont", "isType3Font", "italic", "missingFile", "remeasure", "vertical"];
  static strings = ["fallbackName", "loadedName"];
  static OFFSET_BBOX = Math.ceil(this.bools.length * 2 / 8);
  static OFFSET_FONT_MATRIX = this.OFFSET_BBOX + 1 + 2 * 4;
  static OFFSET_STRINGS = this.OFFSET_FONT_MATRIX + 1 + 8 * 6;
}
class PATTERN_INFO {
  static KIND = 0;
  static HAS_BBOX = 1;
  static HAS_BACKGROUND = 2;
  static SHADING_TYPE = 3;
  static N_COORD = 4;
  static N_COLOR = 8;
  static N_STOP = 12;
  static N_FIGURES = 16;
}
class InfoUtils {
  static get decoder() {
    return shadow(this, "decoder", new TextDecoder());
  }
  static get encoder() {
    return shadow(this, "encoder", new TextEncoder());
  }
}

;// ./src/display/obj_bin_transform_display.js


function readString(buffer, view, index, offset = 0) {
  const {
    decoder
  } = InfoUtils;
  for (let i = 0; i < index; i++) {
    offset += view.getUint32(offset) + 4;
  }
  const length = view.getUint32(offset);
  return decoder.decode(new Uint8Array(buffer, offset + 4, length));
}
class CssFontInfo {
  #buffer;
  #view;
  constructor(buffer) {
    this.#buffer = buffer;
    this.#view = new DataView(buffer);
  }
  #readString(index) {
    assert(index < CSS_FONT_INFO.strings.length, "Invalid string index");
    return readString(this.#buffer, this.#view, index);
  }
  get fontFamily() {
    return shadow(this, "fontFamily", this.#readString(0));
  }
  get fontWeight() {
    return shadow(this, "fontWeight", this.#readString(1));
  }
  get italicAngle() {
    return shadow(this, "italicAngle", this.#readString(2));
  }
}
class SystemFontInfo {
  #buffer;
  #view;
  constructor(buffer) {
    this.#buffer = buffer;
    this.#view = new DataView(buffer);
  }
  #readString(index) {
    assert(index < SYSTEM_FONT_INFO.strings.length, "Invalid string index");
    return readString(this.#buffer, this.#view, index, 4);
  }
  get css() {
    return shadow(this, "css", this.#readString(0));
  }
  get loadedName() {
    return shadow(this, "loadedName", this.#readString(1));
  }
  get baseFontName() {
    return shadow(this, "baseFontName", this.#readString(2));
  }
  get src() {
    return shadow(this, "src", this.#readString(3));
  }
  get style() {
    let offset = 0;
    offset += 4 + this.#view.getUint32(offset);
    const style = readString(this.#buffer, this.#view, 0, offset),
      weight = readString(this.#buffer, this.#view, 1, offset);
    return shadow(this, "style", {
      style,
      weight
    });
  }
}
class FontInfo {
  #buffer;
  #view;
  constructor(buffer) {
    this.#buffer = buffer;
    this.#view = new DataView(buffer);
  }
  #readBoolean(index) {
    assert(index < FONT_INFO.bools.length, "Invalid boolean index");
    const byteOffset = Math.floor(index / 4);
    const bitOffset = index * 2 % 8;
    const value = this.#view.getUint8(byteOffset) >> bitOffset & 0x03;
    return value === 0x00 ? undefined : value === 0x02;
  }
  get black() {
    return shadow(this, "black", this.#readBoolean(0));
  }
  get bold() {
    return shadow(this, "bold", this.#readBoolean(1));
  }
  get disableFontFace() {
    return shadow(this, "disableFontFace", this.#readBoolean(2));
  }
  get fontExtraProperties() {
    return shadow(this, "fontExtraProperties", this.#readBoolean(3));
  }
  get isInvalidPDFjsFont() {
    return shadow(this, "isInvalidPDFjsFont", this.#readBoolean(4));
  }
  get isType3Font() {
    return shadow(this, "isType3Font", this.#readBoolean(5));
  }
  get italic() {
    return shadow(this, "italic", this.#readBoolean(6));
  }
  get missingFile() {
    return shadow(this, "missingFile", this.#readBoolean(7));
  }
  get remeasure() {
    return shadow(this, "remeasure", this.#readBoolean(8));
  }
  get vertical() {
    return shadow(this, "vertical", this.#readBoolean(9));
  }
  #readArray(offset, arrLen, lookupName, increment) {
    const len = this.#view.getUint8(offset++);
    if (len === 0) {
      return undefined;
    }
    assert(len === arrLen, "Invalid array length.");
    const arr = new Array(len);
    for (let i = 0; i < len; i++) {
      arr[i] = this.#view[lookupName](offset, true);
      offset += increment;
    }
    return arr;
  }
  get bbox() {
    return shadow(this, "bbox", this.#readArray(FONT_INFO.OFFSET_BBOX, 4, "getInt16", 2));
  }
  get fontMatrix() {
    return shadow(this, "fontMatrix", this.#readArray(FONT_INFO.OFFSET_FONT_MATRIX, 6, "getFloat64", 8));
  }
  #readString(index) {
    assert(index < FONT_INFO.strings.length, "Invalid string index");
    return readString(this.#buffer, this.#view, index, FONT_INFO.OFFSET_STRINGS + 4);
  }
  get fallbackName() {
    return shadow(this, "fallbackName", this.#readString(0));
  }
  get loadedName() {
    return shadow(this, "loadedName", this.#readString(1));
  }
  #getBufferOffset(index) {
    let offset = FONT_INFO.OFFSET_STRINGS;
    for (let i = 0; i <= index; i++) {
      offset += 4 + this.#view.getUint32(offset);
    }
    const length = this.#view.getUint32(offset);
    return {
      offset,
      length
    };
  }
  get data() {
    const {
      offset,
      length
    } = this.#getBufferOffset(2);
    return !length ? undefined : new Uint8Array(this.#buffer, offset + 4, length);
  }
  clearData() {
    const {
      offset,
      length
    } = this.#getBufferOffset(2);
    if (!length) {
      return;
    }
    this.#view.setUint32(offset, 0);
    this.#buffer = new Uint8Array(this.#buffer, 0, offset + 4).slice().buffer;
    this.#view = new DataView(this.#buffer);
  }
  get cssFontInfo() {
    const {
      offset,
      length
    } = this.#getBufferOffset(1);
    let info = null;
    if (length) {
      const data = new Uint8Array(this.#buffer, offset + 4, length).slice();
      info = new CssFontInfo(data.buffer);
    }
    return shadow(this, "cssFontInfo", info);
  }
  get systemFontInfo() {
    const {
      offset,
      length
    } = this.#getBufferOffset(0);
    let info = null;
    if (length) {
      const data = new Uint8Array(this.#buffer, offset + 4, length).slice();
      info = new SystemFontInfo(data.buffer);
    }
    return shadow(this, "systemFontInfo", info);
  }
}
class PatternInfo {
  constructor(buffer) {
    this.buffer = buffer;
    this.view = new DataView(buffer);
    this.data = new Uint8Array(buffer);
  }
  getIR() {
    const dataView = this.view;
    const kind = this.data[PATTERN_INFO.KIND];
    const hasBBox = !!this.data[PATTERN_INFO.HAS_BBOX];
    const hasBackground = !!this.data[PATTERN_INFO.HAS_BACKGROUND];
    const nCoord = dataView.getUint32(PATTERN_INFO.N_COORD, true);
    const nColor = dataView.getUint32(PATTERN_INFO.N_COLOR, true);
    const nStop = dataView.getUint32(PATTERN_INFO.N_STOP, true);
    let offset = 20;
    const coords = new Float32Array(this.buffer, offset, nCoord * 2);
    offset += nCoord * 8;
    const colors = new Uint8Array(this.buffer, offset, nColor * 4);
    offset += nColor * 4;
    const stops = [];
    for (let i = 0; i < nStop; ++i) {
      const p = dataView.getFloat32(offset, true);
      offset += 4;
      const rgb = dataView.getUint32(offset, true);
      offset += 4;
      stops.push([p, `#${rgb.toString(16).padStart(6, "0")}`]);
    }
    let bbox = null;
    if (hasBBox) {
      bbox = [];
      for (let i = 0; i < 4; ++i) {
        bbox.push(dataView.getFloat32(offset, true));
        offset += 4;
      }
    }
    let background = null;
    if (hasBackground) {
      background = new Uint8Array(this.buffer, offset, 3);
      offset += 3;
    }
    if (kind === 1) {
      return ["RadialAxial", "axial", bbox, stops, [coords[0], coords[1]], [coords[2], coords[3]], null, null];
    }
    if (kind === 2) {
      return ["RadialAxial", "radial", bbox, stops, [coords[0], coords[1]], [coords[3], coords[4]], coords[2], coords[5]];
    }
    if (kind === 3) {
      const shadingType = this.data[PATTERN_INFO.SHADING_TYPE];
      let bounds = null;
      if (coords.length > 0) {
        bounds = BBOX_INIT.slice();
        for (let i = 0, ii = coords.length; i < ii; i += 2) {
          Util.pointBoundingBox(coords[i], coords[i + 1], bounds);
        }
      }
      return ["Mesh", shadingType, coords, colors, nCoord, bounds, bbox, background];
    }
    throw new Error(`Unsupported pattern kind: ${kind}`);
  }
}
class FontPathInfo {
  #buffer;
  constructor(buffer) {
    this.#buffer = buffer;
  }
  get path() {
    if (FeatureTest.isFloat16ArraySupported) {
      return new Float16Array(this.#buffer);
    }
    return new Float32Array(this.#buffer);
  }
}

;// ./src/display/pdf_objects.js
const INITIAL_DATA = Symbol("INITIAL_DATA");
const dataObj = () => ({
  ...Promise.withResolvers(),
  data: INITIAL_DATA
});
class PDFObjects {
  #objs = new Map();
  get(objId, callback = null, errorCallback = null) {
    if (callback) {
      const obj = this.#objs.getOrInsertComputed(objId, dataObj);
      obj.promise.then(() => callback(obj.data), errorCallback);
      return null;
    }
    const obj = this.#objs.get(objId);
    if (!obj || obj.data === INITIAL_DATA) {
      throw new Error(`Requesting object that isn't resolved yet ${objId}.`);
    }
    return obj.data;
  }
  has(objId) {
    const obj = this.#objs.get(objId);
    return !!obj && obj.data !== INITIAL_DATA;
  }
  delete(objId) {
    const obj = this.#objs.get(objId);
    if (!obj || obj.data === INITIAL_DATA) {
      return false;
    }
    this.#objs.delete(objId);
    return true;
  }
  resolve(objId, data = null) {
    const obj = this.#objs.getOrInsertComputed(objId, dataObj);
    if (obj.data !== INITIAL_DATA) {
      throw new Error(`Object already resolved ${objId}.`);
    }
    obj.data = data;
    obj.resolve();
  }
  reject(objId, reason) {
    const obj = this.#objs.getOrInsertComputed(objId, dataObj);
    if (obj.data !== INITIAL_DATA) {
      return;
    }
    obj.promise.catch(() => {});
    obj.reject(reason);
  }
  clear() {
    for (const {
      data
    } of this.#objs.values()) {
      data?.bitmap?.close();
    }
    this.#objs.clear();
  }
  *[Symbol.iterator]() {
    for (const [objId, {
      data
    }] of this.#objs) {
      if (data !== INITIAL_DATA) {
        yield [objId, data];
      }
    }
  }
}

;// ./src/display/object_handler.js




class ObjectHandler {
  constructor({
    messageHandler,
    commonObjs,
    fontLoader,
    pageCache,
    pdfBug = false,
    shouldCreatePageObjs = false
  }) {
    this.messageHandler = messageHandler;
    this.commonObjs = commonObjs;
    this.fontLoader = fontLoader;
    this.pageCache = pageCache;
    this.pdfBug = pdfBug;
    this.shouldCreatePageObjs = shouldCreatePageObjs;
  }
  resolveCommonObject(id, type, exportedData) {
    if (type === "CopyLocalImage") {
      const {
        imageRef
      } = exportedData;
      assert(imageRef, "The imageRef must be defined.");
      for (const pageOrObjs of this.pageCache.values()) {
        const objs = pageOrObjs.objs || pageOrObjs;
        for (const [, data] of objs) {
          if (data?.ref !== imageRef) {
            continue;
          }
          if (!data.dataLen) {
            return null;
          }
          const copy = structuredClone(data);
          this.commonObjs.resolve(id, copy);
          return data.dataLen;
        }
      }
      return null;
    }
    switch (type) {
      case "Font":
        if ("error" in exportedData) {
          const exportedError = exportedData.error;
          warn(`Error during font loading: ${exportedError}`);
          this.commonObjs.resolve(id, exportedError);
          break;
        }
        const fontData = new FontInfo(exportedData.buffer);
        const inspectFont = this.pdfBug && globalThis.FontInspector?.enabled ? (font, url) => globalThis.FontInspector.fontAdded(font, url) : null;
        const font = new FontFaceObject(fontData, inspectFont, exportedData.charProcOperatorList, exportedData.extra);
        this.fontLoader.bind(font).catch(() => this.messageHandler.sendWithPromise("FontFallback", {
          id
        }).catch(reason => {
          warn(`FontFallback failed for "${id}": ${reason}`);
        })).finally(() => {
          if (!font.fontExtraProperties) {
            font.clearData();
          }
          this.commonObjs.resolve(id, font);
        });
        break;
      case "FontPath":
        this.commonObjs.resolve(id, new FontPathInfo(exportedData));
        break;
      case "Image":
        this.commonObjs.resolve(id, exportedData);
        break;
      case "Pattern":
        const pattern = new PatternInfo(exportedData);
        this.commonObjs.resolve(id, pattern.getIR());
        break;
      default:
        throw new Error(`Got unknown common object type ${type}`);
    }
    return null;
  }
  resolveObject(id, pageProxyId, type, exportedData) {
    let pageOrObjs = this.pageCache.get(pageProxyId);
    if (!pageOrObjs) {
      if (!this.shouldCreatePageObjs) {
        return false;
      }
      pageOrObjs = new PDFObjects();
      this.pageCache.set(pageProxyId, pageOrObjs);
    }
    const objs = pageOrObjs.objs || pageOrObjs;
    if (objs.has(id)) {
      return false;
    }
    if (pageOrObjs._intentStates?.size === 0) {
      exportedData?.bitmap?.close();
      return false;
    }
    switch (type) {
      case "Image":
      case "Pattern":
        objs.resolve(id, exportedData);
        return true;
      default:
        throw new Error(`Got unknown object type ${type}`);
    }
  }
}

;// ./src/display/optional_content_config.js


const INTERNAL = Symbol("INTERNAL");
class OptionalContentGroup {
  #isDisplay = false;
  #isPrint = false;
  #userSet = false;
  #visible = true;
  constructor(renderingIntent, {
    name,
    intent,
    usage,
    rbGroups
  }) {
    this.#isDisplay = !!(renderingIntent & RenderingIntentFlag.DISPLAY);
    this.#isPrint = !!(renderingIntent & RenderingIntentFlag.PRINT);
    this.name = name;
    this.intent = intent;
    this.usage = usage;
    this.rbGroups = rbGroups;
  }
  get visible() {
    if (this.#userSet) {
      return this.#visible;
    }
    if (!this.#visible) {
      return false;
    }
    const {
      print,
      view
    } = this.usage;
    if (this.#isDisplay) {
      return view?.viewState !== "OFF";
    } else if (this.#isPrint) {
      return print?.printState !== "OFF";
    }
    return true;
  }
  _setVisible(internal, visible, userSet = false) {
    if (internal !== INTERNAL) {
      unreachable("Internal method `_setVisible` called.");
    }
    this.#userSet = userSet;
    this.#visible = visible;
  }
  get serializable() {
    return {
      userSet: this.#userSet,
      visible: this.#visible
    };
  }
}
class OptionalContentConfig {
  #cachedGetHash = null;
  #groups = new Map();
  #initialHash = null;
  #order = null;
  #rawData;
  creator = null;
  name = null;
  constructor(data, renderingIntent = RenderingIntentFlag.DISPLAY, groupState = null) {
    this.#rawData = data;
    this.renderingIntent = renderingIntent;
    if (data === null) {
      return;
    }
    this.name = data.name;
    this.creator = data.creator;
    this.#order = data.order;
    for (const group of data.groups) {
      this.#groups.set(group.id, new OptionalContentGroup(renderingIntent, group));
    }
    if (groupState) {
      if (groupState.size !== this.#groups.size) {
        unreachable("Incorrect serialized groupState.");
      }
      for (const [id, group] of groupState) {
        this.#groups.get(id)._setVisible(INTERNAL, group.visible, group.userSet);
      }
    } else {
      if (data.baseState === "OFF") {
        for (const group of this.#groups.values()) {
          group._setVisible(INTERNAL, false);
        }
      }
      for (const on of data.on) {
        this.#groups.get(on)._setVisible(INTERNAL, true);
      }
      for (const off of data.off) {
        this.#groups.get(off)._setVisible(INTERNAL, false);
      }
    }
    this.#initialHash = this.getHash();
  }
  #evaluateVisibilityExpression(array) {
    const length = array.length;
    if (length < 2) {
      return true;
    }
    const operator = array[0];
    for (let i = 1; i < length; i++) {
      const element = array[i];
      let state;
      if (Array.isArray(element)) {
        state = this.#evaluateVisibilityExpression(element);
      } else if (this.#groups.has(element)) {
        state = this.#groups.get(element).visible;
      } else {
        warn(`Optional content group not found: ${element}`);
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
  isVisible(group) {
    if (this.#groups.size === 0) {
      return true;
    }
    if (!group) {
      info("Optional content group not defined.");
      return true;
    }
    if (group.type === "OCG") {
      if (!this.#groups.has(group.id)) {
        warn(`Optional content group not found: ${group.id}`);
        return true;
      }
      return this.#groups.get(group.id).visible;
    } else if (group.type === "OCMD") {
      if (group.expression) {
        return this.#evaluateVisibilityExpression(group.expression);
      }
      if (!group.policy || group.policy === "AnyOn") {
        for (const id of group.ids) {
          if (!this.#groups.has(id)) {
            warn(`Optional content group not found: ${id}`);
            return true;
          }
          if (this.#groups.get(id).visible) {
            return true;
          }
        }
        return false;
      } else if (group.policy === "AllOn") {
        for (const id of group.ids) {
          if (!this.#groups.has(id)) {
            warn(`Optional content group not found: ${id}`);
            return true;
          }
          if (!this.#groups.get(id).visible) {
            return false;
          }
        }
        return true;
      } else if (group.policy === "AnyOff") {
        for (const id of group.ids) {
          if (!this.#groups.has(id)) {
            warn(`Optional content group not found: ${id}`);
            return true;
          }
          if (!this.#groups.get(id).visible) {
            return true;
          }
        }
        return false;
      } else if (group.policy === "AllOff") {
        for (const id of group.ids) {
          if (!this.#groups.has(id)) {
            warn(`Optional content group not found: ${id}`);
            return true;
          }
          if (this.#groups.get(id).visible) {
            return false;
          }
        }
        return true;
      }
      warn(`Unknown optional content policy ${group.policy}.`);
      return true;
    }
    warn(`Unknown group type ${group.type}.`);
    return true;
  }
  setVisibility(id, visible = true, preserveRB = true) {
    const group = this.#groups.get(id);
    if (!group) {
      warn(`Optional content group not found: ${id}`);
      return;
    }
    if (preserveRB && visible && group.rbGroups.length) {
      for (const rbGroup of group.rbGroups) {
        for (const otherId of rbGroup) {
          if (otherId !== id) {
            this.#groups.get(otherId)?._setVisible(INTERNAL, false, true);
          }
        }
      }
    }
    group._setVisible(INTERNAL, !!visible, true);
    this.#cachedGetHash = null;
  }
  setOCGState({
    state,
    preserveRB
  }) {
    let operator;
    for (const elem of state) {
      switch (elem) {
        case "ON":
        case "OFF":
        case "Toggle":
          operator = elem;
          continue;
      }
      const group = this.#groups.get(elem);
      if (!group) {
        continue;
      }
      switch (operator) {
        case "ON":
          this.setVisibility(elem, true, preserveRB);
          break;
        case "OFF":
          this.setVisibility(elem, false, preserveRB);
          break;
        case "Toggle":
          this.setVisibility(elem, !group.visible, preserveRB);
          break;
      }
    }
    this.#cachedGetHash = null;
  }
  get hasInitialVisibility() {
    return this.#initialHash === null || this.getHash() === this.#initialHash;
  }
  getOrder() {
    if (!this.#groups.size) {
      return null;
    }
    return this.#order ? this.#order.slice() : [...this.#groups.keys()];
  }
  getGroup(id) {
    return this.#groups.get(id) || null;
  }
  getHash() {
    if (this.#cachedGetHash !== null) {
      return this.#cachedGetHash;
    }
    const hash = new MurmurHash3_64();
    for (const [id, group] of this.#groups) {
      hash.update(`${id}:${group.visible}`);
    }
    return this.#cachedGetHash = hash.hexdigest();
  }
  [Symbol.iterator]() {
    return this.#groups.entries();
  }
  get serializable() {
    const groupState = new Map();
    for (const [id, group] of this.#groups) {
      groupState.set(id, group.serializable);
    }
    return {
      data: this.#rawData,
      renderingIntent: this.renderingIntent,
      groupState
    };
  }
  static fromSerializable({
    data,
    renderingIntent,
    groupState
  }) {
    return new OptionalContentConfig(data, renderingIntent, groupState);
  }
}

;// ./src/display/pages_mapper.js


class PagesMapper {
  #pageNumberToId = null;
  #prevPageNumbers = null;
  #pagesNumber = 0;
  #initialPagesNumber = 0;
  #clipboard = null;
  #savedData = null;
  get pagesNumber() {
    return this.#pagesNumber;
  }
  set pagesNumber(n) {
    if (this.#pagesNumber === n) {
      return;
    }
    this.#pagesNumber = this.#initialPagesNumber = n;
    this.#pageNumberToId = null;
    this.#prevPageNumbers = null;
  }
  #ensureInit() {
    if (this.#pageNumberToId) {
      return;
    }
    const n = this.#pagesNumber;
    const pageNumberToId = this.#pageNumberToId = new Uint32Array(n);
    for (let i = 0; i < n; i++) {
      pageNumberToId[i] = i + 1;
    }
    this.#prevPageNumbers = new Int32Array(pageNumberToId);
  }
  #buildIdToPageNumber() {
    const idToPageNumber = new Map();
    const pageNumberToId = this.#pageNumberToId;
    for (let i = 0, ii = this.#pagesNumber; i < ii; i++) {
      const id = pageNumberToId[i];
      const pageNumbers = idToPageNumber.get(id);
      if (pageNumbers) {
        pageNumbers.push(i + 1);
      } else {
        idToPageNumber.set(id, [i + 1]);
      }
    }
    return idToPageNumber;
  }
  movePages(selectedPages, pagesToMove, index) {
    this.#ensureInit();
    const pageNumberToId = this.#pageNumberToId;
    const movedCount = pagesToMove.length;
    const mappedPagesToMove = new Uint32Array(movedCount);
    let removedBeforeTarget = 0;
    for (let i = 0; i < movedCount; i++) {
      const pageIndex = pagesToMove[i] - 1;
      mappedPagesToMove[i] = pageNumberToId[pageIndex];
      if (pageIndex < index) {
        removedBeforeTarget++;
      }
    }
    const pagesNumber = this.#pagesNumber;
    const remainingLen = pagesNumber - movedCount;
    const prevPageNumbers = new Int32Array(pagesNumber);
    const adjustedTarget = MathClamp(index - removedBeforeTarget, 0, remainingLen);
    for (let i = 0, r = 0; i < pagesNumber; i++) {
      if (!selectedPages.has(i + 1)) {
        pageNumberToId[r] = pageNumberToId[i];
        prevPageNumbers[r++] = i + 1;
      }
    }
    pageNumberToId.copyWithin(adjustedTarget + movedCount, adjustedTarget, remainingLen);
    pageNumberToId.set(mappedPagesToMove, adjustedTarget);
    prevPageNumbers.copyWithin(adjustedTarget + movedCount, adjustedTarget, remainingLen);
    prevPageNumbers.set(pagesToMove, adjustedTarget);
    this.#prevPageNumbers = prevPageNumbers;
    if (pagesNumber === this.#initialPagesNumber && pageNumberToId.every((id, i) => id === i + 1)) {
      this.#pageNumberToId = null;
    }
  }
  deletePages(pagesToDelete) {
    this.#ensureInit();
    const pageNumberToId = this.#pageNumberToId;
    const prevIdToPageNumber = this.#buildIdToPageNumber();
    this.#savedData = {
      pageNumberToId: pageNumberToId.slice(),
      pagesNumber: this.#pagesNumber,
      prevPageNumbers: this.#prevPageNumbers.slice()
    };
    const newN = this.#pagesNumber - pagesToDelete.length;
    this.#pagesNumber = newN;
    const newPageNumberToId = this.#pageNumberToId = new Uint32Array(newN);
    this.#prevPageNumbers = new Int32Array(newN);
    let sourceIndex = 0;
    let destIndex = 0;
    for (const pageNumber of pagesToDelete) {
      const pageIndex = pageNumber - 1;
      if (pageIndex !== sourceIndex) {
        newPageNumberToId.set(pageNumberToId.subarray(sourceIndex, pageIndex), destIndex);
        destIndex += pageIndex - sourceIndex;
      }
      sourceIndex = pageIndex + 1;
    }
    if (sourceIndex < pageNumberToId.length) {
      newPageNumberToId.set(pageNumberToId.subarray(sourceIndex), destIndex);
    }
    this.#updatePrevPageNumbers(prevIdToPageNumber, new Set(pagesToDelete));
  }
  cancelDelete() {
    if (this.#savedData) {
      this.#pageNumberToId = this.#savedData.pageNumberToId;
      this.#pagesNumber = this.#savedData.pagesNumber;
      this.#prevPageNumbers = this.#savedData.prevPageNumbers;
      this.#savedData = null;
    }
  }
  cleanSavedData() {
    this.#savedData = null;
  }
  copyPages(pagesToCopy) {
    this.#ensureInit();
    this.#clipboard = {
      pageNumbers: pagesToCopy,
      pageIds: pagesToCopy.map(n => this.#pageNumberToId[n - 1])
    };
  }
  cancelCopy() {
    this.#clipboard = null;
  }
  pastePages(index) {
    this.#ensureInit();
    const pageNumberToId = this.#pageNumberToId;
    const prevIdToPageNumber = this.#buildIdToPageNumber();
    const {
      pageNumbers: copiedPageNumbers,
      pageIds: copiedPageIds
    } = this.#clipboard;
    const newN = this.#pagesNumber + copiedPageNumbers.length;
    this.#pagesNumber = newN;
    const newPageNumberToId = this.#pageNumberToId = new Uint32Array(newN);
    this.#prevPageNumbers = new Int32Array(newN);
    newPageNumberToId.set(pageNumberToId.subarray(0, index), 0);
    newPageNumberToId.set(copiedPageIds, index);
    newPageNumberToId.set(pageNumberToId.subarray(index), index + copiedPageNumbers.length);
    this.#updatePrevPageNumbers(prevIdToPageNumber, null, index, copiedPageNumbers);
    this.#clipboard = null;
  }
  #updatePrevPageNumbers(prevIdToPageNumber, deletedPageNumbers = null, pasteIndex = -1, copiedPageNumbers = null) {
    const prevPageNumbers = this.#prevPageNumbers;
    const newPageNumberToId = this.#pageNumberToId;
    const pasteEnd = pasteIndex + (copiedPageNumbers?.length ?? 0);
    const idsIndices = new Map();
    for (let i = 0, ii = this.#pagesNumber; i < ii; i++) {
      if (i >= pasteIndex && i < pasteEnd) {
        prevPageNumbers[i] = -copiedPageNumbers[i - pasteIndex];
        continue;
      }
      const id = newPageNumberToId[i];
      const oldPositions = prevIdToPageNumber.get(id);
      let j = idsIndices.get(id) || 0;
      if (deletedPageNumbers && oldPositions) {
        while (j < oldPositions.length && deletedPageNumbers.has(oldPositions[j])) {
          j++;
        }
      }
      prevPageNumbers[i] = oldPositions?.[j];
      idsIndices.set(id, j + 1);
    }
  }
  hasBeenAltered() {
    return this.#pageNumberToId !== null;
  }
  #buildCopyLevels(extractedPageNumbers = null) {
    if (!this.#pageNumberToId) {
      return null;
    }
    const copyLevels = new Int32Array(this.#pagesNumber).fill(-1);
    const counts = new Map();
    if (extractedPageNumbers) {
      for (const pageNumber of extractedPageNumbers) {
        const id = this.getPageId(pageNumber);
        const level = counts.get(id) ?? 0;
        counts.set(id, level + 1);
        copyLevels[pageNumber - 1] = level;
      }
    } else {
      for (let i = 0, ii = this.#pagesNumber; i < ii; i++) {
        const id = this.#pageNumberToId[i];
        const level = counts.get(id) ?? 0;
        counts.set(id, level + 1);
        copyLevels[i] = level;
      }
    }
    return copyLevels;
  }
  getPageMappingForSaving(idToPageNumber = null, copyLevels = this.#buildCopyLevels()) {
    idToPageNumber ??= this.#buildIdToPageNumber();
    let nCopy = 0;
    for (const pageNumbers of idToPageNumber.values()) {
      nCopy = Math.max(nCopy, pageNumbers.length);
    }
    const extractParams = new Array(nCopy);
    for (let i = 0; i < nCopy; i++) {
      extractParams[i] = {
        document: null,
        pageIndices: [],
        includePages: []
      };
    }
    for (const [id, pageNumbers] of idToPageNumber) {
      for (let i = 0, ii = pageNumbers.length; i < ii; i++) {
        extractParams[i].includePages.push([id - 1, pageNumbers[i] - 1]);
      }
    }
    for (const {
      includePages,
      pageIndices
    } of extractParams) {
      includePages.sort((a, b) => a[0] - b[0]);
      for (let i = 0, ii = includePages.length; i < ii; i++) {
        pageIndices.push(includePages[i][1]);
        includePages[i] = includePages[i][0];
      }
    }
    return {
      pageInfos: extractParams,
      copyLevels
    };
  }
  extractPages(extractedPageNumbers) {
    extractedPageNumbers = Array.from(extractedPageNumbers).sort((a, b) => a - b);
    const usedIds = new Map();
    for (let i = 0, ii = extractedPageNumbers.length; i < ii; i++) {
      const id = this.getPageId(extractedPageNumbers[i]);
      const usedPageNumbers = usedIds.getOrInsertComputed(id, makeArr);
      usedPageNumbers.push(i + 1);
    }
    return this.getPageMappingForSaving(usedIds, this.#buildCopyLevels(extractedPageNumbers));
  }
  getPrevPageNumber(pageNumber) {
    return this.#prevPageNumbers?.[pageNumber - 1] ?? 0;
  }
  getPageNumber(id) {
    if (!this.#pageNumberToId) {
      return id;
    }
    const pageNumberToId = this.#pageNumberToId;
    for (let i = 0, ii = this.#pagesNumber; i < ii; i++) {
      if (pageNumberToId[i] === id) {
        return i + 1;
      }
    }
    return 0;
  }
  getPageId(pageNumber) {
    return this.#pageNumberToId?.[pageNumber - 1] ?? pageNumber;
  }
  getMapping() {
    return this.#pageNumberToId?.subarray(0, this.pagesNumber);
  }
}

;// ./src/display/renderer_worker_proxy.js







const PORT_CONNECTION_TIMEOUT = 5000;
function closeFrame({
  bitmap,
  annotationBitmaps
}) {
  bitmap?.close();
  if (annotationBitmaps) {
    for (const [,, annotationBitmap] of annotationBitmaps) {
      annotationBitmap.close();
    }
  }
}
class WorkerRenderTask {
  #annotationCanvasMap;
  #cancelled = false;
  #canvas;
  #canvasFactory;
  #filteredLength = 0;
  #id;
  #initParams;
  #onError;
  #onFrame;
  #operatorListState;
  #rendererWorker;
  #renderTasks;
  imageCoordinates = null;
  recordedBBoxes = null;
  constructor({
    rendererWorker,
    renderTasks,
    canvas,
    canvasFactory,
    annotationCanvasMap,
    operatorListState,
    initParams,
    onFrame,
    onError
  }) {
    this.#rendererWorker = rendererWorker;
    this.#renderTasks = renderTasks;
    this.#canvas = canvas;
    this.#canvasFactory = canvasFactory;
    this.#annotationCanvasMap = annotationCanvasMap;
    this.#operatorListState = operatorListState;
    this.#initParams = initParams;
    this.#id = initParams.renderTaskId;
    this.#onFrame = onFrame;
    this.#onError = onError;
  }
  async initialize(transparency, optionalContentConfig) {
    try {
      await this.#rendererWorker.promise;
    } catch {
      return false;
    }
    if (!this.#rendererWorker.messageHandler || this.#cancelled) {
      return false;
    }
    try {
      await this.#rendererWorker.sendWithPromise("InitializeGraphics", {
        ...this.#initParams,
        width: this.#canvas.width,
        height: this.#canvas.height,
        transparency,
        optionalContentConfig: optionalContentConfig.serializable
      });
    } catch (ex) {
      if (!this.#cancelled) {
        warn(`Failed to initialize graphics in renderer worker: ${ex.message}. ` + "Falling back to main-thread rendering.");
      }
      return false;
    }
    if (!this.#cancelled) {
      this.#renderTasks.set(this.#id, this);
    }
    return true;
  }
  async executeOperatorList(operatorList, operatorListIdx, operationsFilter) {
    const handler = this.#rendererWorker.messageHandler;
    if (!handler) {
      throw new Error("Renderer worker was destroyed during rendering.");
    }
    const {
      lastChunk
    } = operatorList;
    const end = operatorList.argsArray.length;
    const operatorListState = this.#operatorListState;
    if (operatorListState.sentLength < end) {
      const start = operatorListState.sentLength;
      handler.send("AppendOperatorList", {
        pageProxyId: this.#initParams.pageProxyId,
        operatorListId: operatorListState.id,
        fnArray: operatorList.fnArray.slice(start, end),
        argsArray: operatorList.argsArray.slice(start, end)
      });
      operatorListState.sentLength = end;
    }
    let operationsFilterMask = null;
    if (operationsFilter && this.#filteredLength < end) {
      const start = this.#filteredLength;
      operationsFilterMask = new Uint8Array(end - start);
      for (let i = start; i < end; i++) {
        operationsFilterMask[i - start] = operationsFilter(i, operatorList) ? 1 : 0;
      }
      this.#filteredLength = end;
    }
    const response = await this.#rendererWorker.sendWithPromise("ExecuteOperatorList", {
      renderTaskId: this.#id,
      operatorListIdx,
      operatorListLength: end,
      operationsFilterMask,
      lastChunk
    }).catch(reason => {
      if (!this.#cancelled) {
        throw reason;
      }
      return {
        operatorListIdx,
        aborted: true
      };
    });
    if (response.aborted && !this.#cancelled) {
      throw new Error("Render task was aborted in the renderer worker.");
    }
    if (lastChunk && response.operatorListIdx === end) {
      this.#renderTasks.delete(this.#id);
      const {
        recordedBBoxesBuffer,
        imageCoordinates
      } = response;
      if (recordedBBoxesBuffer) {
        this.recordedBBoxes = BBoxReader.fromBuffer(recordedBBoxesBuffer);
      }
      this.imageCoordinates = imageCoordinates ?? null;
    }
    return response.operatorListIdx;
  }
  cancel() {
    this.#cancelled = true;
    this.#renderTasks.delete(this.#id);
    this.#rendererWorker.messageHandler?.send("CleanupRenderTask", {
      renderTaskId: this.#id
    });
  }
  drawFrame(frame) {
    try {
      if (frame.bitmap) {
        const ctx = this.#canvasFactory.getNoAlphaContext(this.#canvas);
        ctx.drawImage(frame.bitmap, 0, 0);
      }
      if (frame.annotationBitmaps) {
        this.#drawAnnotationCanvases(frame.annotationBitmaps);
      }
    } catch (ex) {
      this.#onError(ex);
      return;
    } finally {
      closeFrame(frame);
    }
    this.#onFrame();
  }
  #drawAnnotationCanvases(annotationBitmaps) {
    const annotationCanvasMap = this.#annotationCanvasMap;
    const seen = new Set();
    for (const [id, canvasName, bitmap] of annotationBitmaps) {
      const {
        canvas,
        context
      } = this.#canvasFactory.create(bitmap.width, bitmap.height);
      context.drawImage(bitmap, 0, 0);
      if (!canvasName) {
        annotationCanvasMap.set(id, canvas);
        continue;
      }
      setAnnotationCanvasName(canvas, canvasName);
      if (seen.has(id)) {
        annotationCanvasMap.get(id).push(canvas);
      } else {
        seen.add(id);
        annotationCanvasMap.set(id, [canvas]);
      }
    }
  }
}
class RendererWorker {
  #capability = Promise.withResolvers();
  #enableHWA;
  #enableWebGPU;
  #messageHandler = null;
  #operatorListId = 0;
  #operatorLists = new WeakMap();
  #pendingMessages = [];
  #pendingRequests = new Set();
  #port = null;
  #portNames = null;
  #renderTaskId = 0;
  #renderTasks = new Map();
  #terminateEarly = null;
  #webWorker = null;
  #workerAC = null;
  static #connectionId = 0;
  static #usedPorts = new WeakSet();
  destroyed = false;
  constructor({
    port = null,
    verbosity = getVerbosityLevel(),
    enableHWA = false,
    enableWebGPU = false
  } = {}) {
    this.verbosity = verbosity;
    this.#enableHWA = enableHWA;
    this.#enableWebGPU = enableWebGPU;
    if (port) {
      this.#initializeFromPort(port);
    } else {
      this.#initialize();
    }
  }
  static get isAvailable() {
    return (!!GlobalWorkerOptions.rendererSrc || GlobalWorkerOptions.rendererPorts.length > 0) && typeof Worker !== "undefined" && FeatureTest.isOffscreenCanvasSupported && !!globalThis.document?.fonts;
  }
  get promise() {
    return this.#capability.promise;
  }
  get messageHandler() {
    return this.#messageHandler;
  }
  get port() {
    return this.#port;
  }
  #resolve() {
    this.#messageHandler.on("RenderFrame", frame => {
      const renderTask = this.#renderTasks.get(frame.renderTaskId);
      if (renderTask) {
        renderTask.drawFrame(frame);
      } else {
        closeFrame(frame);
      }
    });
    this.#capability.resolve();
    this.#messageHandler.send("configure", {
      verbosity: this.verbosity,
      enableHWA: this.#enableHWA,
      enableWebGPU: this.#enableWebGPU
    });
    const pendingMessages = this.#pendingMessages;
    this.#pendingMessages = null;
    for (const send of pendingMessages) {
      send();
    }
  }
  #reject(reason) {
    this.#pendingMessages = null;
    this.#capability.reject(reason);
  }
  #initializeFromPort(port) {
    RendererWorker.#usedPorts.add(port);
    this.#port = port;
    const id = RendererWorker.#connectionId++;
    const sourceName = `main${id}`;
    const targetName = `renderer${id}`;
    this.#portNames = {
      sourceName,
      targetName
    };
    const handler = new MessageHandler("main", "renderer", port);
    handler.send("Connect", {
      sourceName: targetName,
      targetName: sourceName
    });
    handler.destroy();
    this.#waitForReady(port, new MessageHandler(sourceName, targetName, port), true);
  }
  #initialize() {
    try {
      const {
        rendererSrc
      } = GlobalWorkerOptions;
      if (!rendererSrc) {
        throw new Error('No "GlobalWorkerOptions.rendererSrc" specified.');
      }
      const worker = new Worker(getWorkerSrc(rendererSrc), {
        type: "module"
      });
      this.#waitForReady(worker, new MessageHandler("main", "renderer", worker), false);
    } catch (reason) {
      this.#reject(reason);
    }
  }
  #waitForReady(worker, messageHandler, isPort) {
    let timeoutId = null;
    const terminateEarly = reason => {
      this.#terminateEarly = null;
      clearTimeout(timeoutId);
      ac.abort();
      messageHandler.destroy();
      if (isPort) {
        this.#port = null;
      } else {
        worker.terminate();
      }
      this.#reject(new Error(`Renderer worker failed to initialize: "${reason?.message ?? reason}".`));
    };
    this.#terminateEarly = terminateEarly;
    const ac = new AbortController();
    const onError = (event, reason) => {
      if (!this.#messageHandler) {
        terminateEarly(reason);
        return;
      }
      event.preventDefault();
      warn(`Renderer worker failed: "${reason}". ` + "Falling back to main-thread rendering.");
      this.destroy();
    };
    worker.addEventListener("error", event => onError(event, event.error?.message ?? event.message), {
      signal: ac.signal
    });
    worker.addEventListener("messageerror", event => onError(event, "Cannot deserialize a message."), {
      signal: ac.signal
    });
    if (isPort) {
      timeoutId = setTimeout(() => terminateEarly("Connection timed out."), PORT_CONNECTION_TIMEOUT);
    }
    messageHandler.on("ready", data => {
      if (!(data?.testObj instanceof Uint8Array)) {
        terminateEarly("TypedArray transfer test failed.");
        return;
      }
      const apiVersion = "6.5.438";
      if (apiVersion !== data.workerVersion) {
        terminateEarly(`The API version "${apiVersion}" does not match the Worker version "${data.workerVersion}".`);
        return;
      }
      this.#terminateEarly = null;
      clearTimeout(timeoutId);
      this.#messageHandler = messageHandler;
      if (!isPort) {
        this.#webWorker = worker;
      }
      this.#workerAC = ac;
      this.#resolve();
    });
  }
  destroy() {
    this.destroyed = true;
    if (this.#port) {
      if (this.#messageHandler) {
        this.#closeStrayFrames(this.#port);
        this.#messageHandler.send("Disconnect", null);
      }
      RendererWorker.#usedPorts.delete(this.#port);
      this.#port = null;
    }
    this.#terminateEarly?.("Worker was destroyed.");
    this.#workerAC?.abort();
    this.#workerAC = null;
    this.#webWorker?.terminate();
    this.#webWorker = null;
    this.#messageHandler?.destroy();
    this.#messageHandler = null;
    for (const reject of this.#pendingRequests) {
      reject(new Error("Renderer worker was destroyed."));
    }
    this.#pendingRequests.clear();
  }
  #closeStrayFrames(port) {
    const {
      sourceName,
      targetName
    } = this.#portNames;
    const ac = new AbortController();
    const timeoutId = setTimeout(() => ac.abort(), PORT_CONNECTION_TIMEOUT);
    port.addEventListener("message", ({
      data
    }) => {
      if (data?.targetName !== sourceName || data.sourceName !== targetName) {
        return;
      }
      if (data.action === "RenderFrame") {
        closeFrame(data.data);
      } else if (data.action === "Disconnected") {
        clearTimeout(timeoutId);
        ac.abort();
      }
    }, {
      signal: ac.signal
    });
  }
  static create({
    ports = [],
    ...params
  } = {}) {
    const port = ports.find(p => !this.#usedPorts.has(p)) ?? null;
    if (!port && ports.length > 0) {
      warn("RendererWorker.create - no unused `rendererPorts` available, " + "falling back to `rendererSrc`.");
    }
    return new RendererWorker({
      ...params,
      port
    });
  }
  sendWithPromise(action, data) {
    const handler = this.#messageHandler;
    if (!handler) {
      return Promise.reject(new Error("Renderer worker was destroyed."));
    }
    const {
      promise,
      resolve,
      reject
    } = Promise.withResolvers();
    this.#pendingRequests.add(reject);
    handler.sendWithPromise(action, data).then(resolve, reject);
    return promise.finally(() => {
      this.#pendingRequests.delete(reject);
    });
  }
  #send(action, data) {
    if (this.#pendingMessages) {
      this.#pendingMessages.push(() => this.#send(action, data));
      return;
    }
    this.#messageHandler?.send(action, data);
  }
  #sendObj(action, data, id, pageProxyId, isFont = false) {
    try {
      if (this.#pendingMessages) {
        const queuedData = isFont ? structuredClone(data) : data;
        this.#pendingMessages.push(() => this.#sendObj(action, queuedData, id, pageProxyId));
        return;
      }
      this.#messageHandler?.send(action, data);
    } catch (reason) {
      warn(`RendererWorker - failed to send "${action}": ${reason}`);
      this.#send("objFailed", {
        id,
        pageProxyId,
        reason: reason.message
      });
    }
  }
  sendCommonObj(id, type, data) {
    this.#sendObj("commonobj", [id, type, data], id, null, type === "Font");
  }
  sendObj(id, pageProxyId, type, data) {
    this.#sendObj("obj", [id, pageProxyId, type, data], id, pageProxyId);
  }
  cleanup(keepLoadedFonts) {
    this.#send("Cleanup", {
      keepLoadedFonts
    });
  }
  cleanupPage(pageProxyId) {
    this.#send("cleanupPage", {
      pageProxyId
    });
  }
  createRenderTask({
    pageProxyId,
    operatorList,
    params,
    pageColors,
    canvasFactory,
    annotationCanvasMap,
    onFrame,
    onError
  }) {
    const {
      canvas,
      canvasContext,
      background
    } = params;
    if (!this.#messageHandler && !this.#pendingMessages || canvasContext || background && typeof background !== "string" || pageColors || params.recordForDebugger) {
      return null;
    }
    const operatorListState = this.#operatorLists.getOrInsertComputed(operatorList, () => ({
      id: this.#operatorListId++,
      sentLength: 0
    }));
    return new WorkerRenderTask({
      rendererWorker: this,
      renderTasks: this.#renderTasks,
      canvas,
      canvasFactory,
      annotationCanvasMap,
      operatorListState,
      initParams: {
        pageProxyId,
        operatorListId: operatorListState.id,
        renderTaskId: this.#renderTaskId++,
        hasAnnotationCanvasMap: !!annotationCanvasMap,
        recordOperations: params.recordOperations,
        recordImages: params.recordImages,
        partialFrames: params.partialFrames,
        transform: params.transform,
        viewport: params.viewport,
        background,
        pixelRatio: OutputScale.pixelRatio
      },
      onFrame,
      onError
    });
  }
}

;// ./src/display/text_layer.js



const MAX_TEXT_DIVS_TO_RENDER = 100000;
const DEFAULT_FONT_SIZE = 30;
class TextLayer {
  #capability = Promise.withResolvers();
  #container = null;
  #disableProcessItems = false;
  #fontInspectorEnabled = !!globalThis.FontInspector?.enabled;
  #imagesHandler = null;
  #lang = null;
  #layoutTextParams = null;
  #pageHeight = 0;
  #pageWidth = 0;
  #pixelRatio = OutputScale.pixelRatio;
  #reader = null;
  #rootContainer = null;
  #rotation = 0;
  #scale = 0;
  #styleCache = Object.create(null);
  #textContentItemsStr = [];
  #textContentSource = null;
  #textDivs = [];
  #transform = null;
  static #ascentCache = new Map();
  static #canvasContexts = new Map();
  static #canvasCtxFonts = new WeakMap();
  static #minFontSize = null;
  static #pendingTextLayers = new Set();
  constructor({
    textContentSource,
    images,
    container,
    viewport
  }) {
    if (textContentSource instanceof ReadableStream) {
      this.#textContentSource = textContentSource;
    } else if (typeof textContentSource === "object") {
      this.#textContentSource = new ReadableStream({
        start(controller) {
          controller.enqueue(textContentSource);
          controller.close();
        }
      });
    } else {
      throw new Error('No "textContentSource" parameter specified.');
    }
    this.#container = this.#rootContainer = container;
    this.#imagesHandler = images;
    this.#scale = viewport.scale * this.#pixelRatio;
    this.#rotation = viewport.rotation;
    this.#layoutTextParams = {
      div: null,
      properties: null,
      ctx: null
    };
    const {
      pageWidth,
      pageHeight,
      pageX,
      pageY
    } = viewport.rawDims;
    this.#transform = [1, 0, 0, -1, -pageX, pageY + pageHeight];
    this.#pageWidth = pageWidth;
    this.#pageHeight = pageHeight;
    TextLayer.#ensureMinFontSizeComputed();
    container.style.setProperty("--min-font-size", TextLayer.#minFontSize);
    setLayerDimensions(container, viewport);
    this.#capability.promise.finally(() => {
      TextLayer.#pendingTextLayers.delete(this);
      this.#layoutTextParams = null;
      this.#styleCache = null;
    }).catch(() => {});
  }
  static get fontFamilyMap() {
    const {
      isWindows,
      isFirefox
    } = FeatureTest.platform;
    return shadow(this, "fontFamilyMap", new Map([["sans-serif", `${isWindows && isFirefox ? "Calibri, " : ""}sans-serif`], ["monospace", `${isWindows && isFirefox ? "Lucida Console, " : ""}monospace`]]));
  }
  render() {
    if (this.#imagesHandler) {
      this.#container.append(this.#imagesHandler.render());
    }
    const pump = () => {
      this.#reader.read().then(({
        value,
        done
      }) => {
        if (done) {
          this.#capability.resolve();
          return;
        }
        this.#lang ??= value.lang;
        Object.assign(this.#styleCache, value.styles);
        this.#processItems(value.items);
        pump();
      }, this.#capability.reject);
    };
    this.#reader = this.#textContentSource.getReader();
    TextLayer.#pendingTextLayers.add(this);
    pump();
    return this.#capability.promise;
  }
  update({
    viewport
  }) {
    const scale = viewport.scale * OutputScale.pixelRatio;
    const rotation = viewport.rotation;
    if (rotation !== this.#rotation) {
      this.#rotation = rotation;
      setLayerDimensions(this.#rootContainer, {
        rotation
      });
    }
    if (scale !== this.#scale) {
      this.#scale = scale;
      this.#pixelRatio = OutputScale.pixelRatio;
    }
  }
  cancel() {
    const abortEx = new AbortException("TextLayer task cancelled.");
    this.#reader?.cancel(abortEx).catch(() => {});
    this.#reader = null;
    this.#capability.reject(abortEx);
  }
  get textDivs() {
    return this.#textDivs;
  }
  get textContentItemsStr() {
    return this.#textContentItemsStr;
  }
  #processItems(items) {
    if (this.#disableProcessItems) {
      return;
    }
    this.#layoutTextParams.ctx ??= TextLayer.#getCtx(this.#lang);
    const textDivs = this.#textDivs,
      textContentItemsStr = this.#textContentItemsStr;
    for (const item of items) {
      if (textDivs.length > MAX_TEXT_DIVS_TO_RENDER) {
        warn("Ignoring additional textDivs for performance reasons.");
        this.#disableProcessItems = true;
        return;
      }
      if (item.str === undefined) {
        if (item.type === "beginMarkedContentProps" || item.type === "beginMarkedContent") {
          const parent = this.#container;
          this.#container = document.createElement("span");
          this.#container.classList.add("markedContent");
          if (item.id) {
            this.#container.setAttribute("id", item.id);
          }
          if (item.tag === "Artifact") {
            this.#container.ariaHidden = true;
          }
          parent.append(this.#container);
        } else if (item.type === "endMarkedContent") {
          this.#container = this.#container.parentNode;
        }
        continue;
      }
      textContentItemsStr.push(item.str);
      this.#appendText(item);
    }
  }
  #appendText(geom) {
    const textDiv = document.createElement("span");
    const textDivProperties = {
      angle: 0,
      canvasWidth: 0,
      hasText: geom.str !== "",
      hasEOL: geom.hasEOL,
      fontSize: 0
    };
    this.#textDivs.push(textDiv);
    const tx = Util.transform(this.#transform, geom.transform);
    let angle = Math.atan2(tx[1], tx[0]);
    const style = this.#styleCache[geom.fontName];
    if (style.vertical) {
      angle += Math.PI / 2;
    }
    let fontFamily = this.#fontInspectorEnabled && style.fontSubstitution || style.fontFamily;
    fontFamily = TextLayer.fontFamilyMap.get(fontFamily) || fontFamily;
    const fontHeight = Math.hypot(tx[2], tx[3]);
    const fontAscent = fontHeight * TextLayer.#getAscent(fontFamily, style, this.#lang);
    let left, top;
    if (angle === 0) {
      left = tx[4];
      top = tx[5] - fontAscent;
    } else {
      left = tx[4] + fontAscent * Math.sin(angle);
      top = tx[5] - fontAscent * Math.cos(angle);
    }
    const divStyle = textDiv.style;
    divStyle.left = `${(100 * left / this.#pageWidth).toFixed(2)}%`;
    divStyle.top = `${(100 * top / this.#pageHeight).toFixed(2)}%`;
    const roundedFontHeight = Math.round(fontHeight * 100) / 100;
    divStyle.setProperty("--font-height", `${roundedFontHeight}px`);
    divStyle.fontFamily = fontFamily;
    textDivProperties.fontSize = roundedFontHeight;
    textDiv.setAttribute("role", "presentation");
    textDiv.textContent = geom.str;
    textDiv.dir = geom.dir;
    if (this.#fontInspectorEnabled) {
      textDiv.dataset.fontName = style.fontSubstitutionLoadedName || geom.fontName;
    }
    if (angle !== 0) {
      textDivProperties.angle = angle * (180 / Math.PI);
    }
    let shouldScaleText = false;
    if (geom.str.length > 1) {
      shouldScaleText = true;
    } else if (geom.str !== " " && geom.transform[0] !== geom.transform[3]) {
      const absScaleX = Math.abs(geom.transform[0]),
        absScaleY = Math.abs(geom.transform[3]);
      if (absScaleX !== absScaleY && Math.max(absScaleX, absScaleY) / Math.min(absScaleX, absScaleY) > 1.5) {
        shouldScaleText = true;
      }
    }
    if (shouldScaleText) {
      textDivProperties.canvasWidth = style.vertical ? geom.height : geom.width;
    }
    this.#layoutTextParams.div = textDiv;
    this.#layoutTextParams.properties = textDivProperties;
    this.#layout(this.#layoutTextParams);
    if (textDivProperties.hasText) {
      this.#container.append(textDiv);
    }
    if (textDivProperties.hasEOL) {
      const br = document.createElement("br");
      br.setAttribute("role", "presentation");
      this.#container.append(br);
    }
  }
  #layout(params) {
    const {
      div,
      properties,
      ctx
    } = params;
    const {
      style
    } = div;
    const {
      canvasWidth,
      fontSize
    } = properties;
    if (canvasWidth !== 0 && fontSize !== 0 && properties.hasText) {
      const {
        fontFamily
      } = style;
      const pixelRatio = this.#pixelRatio;
      const measuredSize = TextLayer.#quantizeFontSize(fontSize * this.#scale / pixelRatio) * pixelRatio;
      TextLayer.#ensureCtxFont(ctx, measuredSize, fontFamily);
      const {
        width
      } = ctx.measureText(div.textContent);
      if (width > 0) {
        style.setProperty("--scale-x", canvasWidth * measuredSize / (width * fontSize));
      }
    }
    if (properties.angle !== 0) {
      style.setProperty("--rotate", `${properties.angle}deg`);
    }
  }
  static cleanup() {
    if (this.#pendingTextLayers.size > 0) {
      return;
    }
    this.#ascentCache.clear();
    for (const {
      canvas
    } of this.#canvasContexts.values()) {
      canvas.remove();
    }
    this.#canvasContexts.clear();
  }
  static #getCtx(lang = null) {
    let ctx = this.#canvasContexts.get(lang ||= "");
    if (!ctx) {
      const canvas = document.createElement("canvas");
      canvas.style.cssText = "position:absolute;top:0;left:0;width:0;height:0;display:none;" + "letter-spacing:normal;word-spacing:normal";
      canvas.lang = lang;
      document.body.append(canvas);
      ctx = canvas.getContext("2d", {
        alpha: false,
        willReadFrequently: true
      });
      this.#canvasContexts.set(lang, ctx);
      this.#canvasCtxFonts.set(ctx, {
        size: 0,
        family: ""
      });
    }
    return ctx;
  }
  static #quantizeFontSize(size) {
    size = Math.fround(size);
    const d = Math.fround(size * ((1 << 17) + 1));
    return Math.fround(d - Math.fround(d - size));
  }
  static #ensureCtxFont(ctx, size, family) {
    const cached = this.#canvasCtxFonts.get(ctx);
    if (size === cached.size && family === cached.family) {
      return;
    }
    ctx.font = `${size}px ${family}`;
    cached.size = size;
    cached.family = family;
  }
  static #ensureMinFontSizeComputed() {
    if (this.#minFontSize !== null) {
      return;
    }
    const div = document.createElement("div");
    div.style.opacity = 0;
    div.style.lineHeight = 1;
    div.style.fontSize = "1px";
    div.style.position = "absolute";
    div.textContent = "X";
    document.body.append(div);
    this.#minFontSize = div.getBoundingClientRect().height;
    div.remove();
  }
  static #getAscent(fontFamily, style, lang) {
    const cachedAscent = this.#ascentCache.get(fontFamily);
    if (cachedAscent) {
      return cachedAscent;
    }
    const ctx = this.#getCtx(lang);
    this.#ensureCtxFont(ctx, DEFAULT_FONT_SIZE, fontFamily);
    const metrics = ctx.measureText("");
    const ascent = metrics.fontBoundingBoxAscent;
    const descent = Math.abs(metrics.fontBoundingBoxDescent);
    let ratio = 0.8;
    if (ascent) {
      ratio = ascent / (ascent + descent);
    } else {
      if (FeatureTest.platform.isFirefox) {
        warn("Enable the `dom.textMetrics.fontBoundingBox.enabled` preference " + "in `about:config` to improve TextLayer rendering.");
      }
      if (style.ascent) {
        ratio = style.ascent;
      } else if (style.descent) {
        ratio = 1 + style.descent;
      }
    }
    this.#ascentCache.set(fontFamily, ratio);
    return ratio;
  }
}

;// ./src/display/api.js



























const RENDERING_CANCELLED_TIMEOUT = 100;
function getDocument(src = {}) {
  const task = new PDFDocumentLoadingTask();
  const {
    docId
  } = task;
  const url = src.url ? getUrlProp(src.url) : null;
  const data = src.data ? getDataProp(src.data) : null;
  const httpHeaders = src.httpHeaders || null;
  const withCredentials = src.withCredentials === true;
  const password = src.password ?? null;
  const rangeTransport = src.range instanceof PDFDataRangeTransport ? src.range : null;
  const rangeChunkSize = Number.isInteger(src.rangeChunkSize) && src.rangeChunkSize > 0 ? src.rangeChunkSize : 2 ** 16;
  let worker = src.worker instanceof PDFWorker ? src.worker : null;
  const verbosity = src.verbosity;
  const docBaseUrl = typeof src.docBaseUrl === "string" && !isDataScheme(src.docBaseUrl) ? src.docBaseUrl : null;
  const cMapUrl = getFactoryUrlProp(src.cMapUrl);
  const cMapPacked = src.cMapPacked !== false;
  const iccUrl = getFactoryUrlProp(src.iccUrl);
  const standardFontDataUrl = getFactoryUrlProp(src.standardFontDataUrl);
  const wasmUrl = getFactoryUrlProp(src.wasmUrl);
  const ignoreErrors = src.stopAtErrors !== true;
  const maxImageSize = Number.isInteger(src.maxImageSize) && src.maxImageSize > -1 ? src.maxImageSize : -1;
  const isOffscreenCanvasSupported = typeof src.isOffscreenCanvasSupported === "boolean" ? src.isOffscreenCanvasSupported : !isNodeJS;
  const isImageDecoderSupported = typeof src.isImageDecoderSupported === "boolean" ? src.isImageDecoderSupported : !isNodeJS;
  const canvasMaxAreaInBytes = Number.isInteger(src.canvasMaxAreaInBytes) ? src.canvasMaxAreaInBytes : -1;
  const disableFontFace = typeof src.disableFontFace === "boolean" ? src.disableFontFace : isNodeJS;
  const fontExtraProperties = src.fontExtraProperties === true;
  const enableXfa = src.enableXfa === true;
  const ownerDocument = src.ownerDocument || globalThis.document;
  const disableRange = src.disableRange === true;
  const disableStream = src.disableStream === true;
  const disableAutoFetch = src.disableAutoFetch === true;
  const pdfBug = src.pdfBug === true;
  const CanvasFactory = src.CanvasFactory || (isNodeJS ? NodeCanvasFactory : DOMCanvasFactory);
  const FilterFactory = src.FilterFactory || (isNodeJS ? NodeFilterFactory : DOMFilterFactory);
  const BinaryDataFactory = src.BinaryDataFactory || (isNodeJS ? NodeBinaryDataFactory : DOMBinaryDataFactory);
  const enableHWA = src.enableHWA === true;
  const enableWebGPU = src.enableWebGPU === true;
  if (enableWebGPU) {
    initGPU();
  }
  const useWasm = src.useWasm !== false;
  const pagesMapper = src.pagesMapper || new PagesMapper();
  const styleElement = null;
  const useSystemFonts = typeof src.useSystemFonts === "boolean" ? src.useSystemFonts : !isNodeJS && !disableFontFace;
  const useWorkerFetch = typeof src.useWorkerFetch === "boolean" ? src.useWorkerFetch : !!(BinaryDataFactory === DOMBinaryDataFactory && cMapUrl && cMapPacked && standardFontDataUrl && wasmUrl && isValidFetchUrl(cMapUrl, document.baseURI) && isValidFetchUrl(standardFontDataUrl, document.baseURI) && isValidFetchUrl(wasmUrl, document.baseURI));
  const disableWorkerRendering = src.disableWorkerRendering === true || !isOffscreenCanvasSupported || ownerDocument !== globalThis.document || !!styleElement || !RendererWorker.isAvailable;
  setVerbosityLevel(verbosity);
  const transportFactory = {
    canvasFactory: new CanvasFactory({
      ownerDocument,
      enableHWA
    }),
    filterFactory: new FilterFactory({
      docId,
      ownerDocument
    }),
    binaryDataFactory: useWorkerFetch ? null : new BinaryDataFactory({
      cMapUrl,
      standardFontDataUrl,
      wasmUrl
    })
  };
  if (!worker) {
    worker = PDFWorker.create({
      verbosity,
      port: GlobalWorkerOptions.workerPort
    });
    task._worker = worker;
  }
  if (!disableWorkerRendering) {
    const rendererWorker = RendererWorker.create({
      verbosity,
      enableHWA,
      enableWebGPU,
      ports: GlobalWorkerOptions.rendererPorts
    });
    rendererWorker.promise.catch(reason => {
      if (!rendererWorker.destroyed) {
        warn(`Renderer worker disabled: ${reason.message}`);
        rendererWorker.destroy();
      }
    });
    task._rendererWorker = rendererWorker;
  }
  const docParams = {
    docId,
    apiVersion: "6.5.438",
    data,
    password,
    disableAutoFetch,
    rangeChunkSize,
    docBaseUrl,
    enableXfa,
    evaluatorOptions: {
      maxImageSize,
      disableFontFace,
      ignoreErrors,
      isOffscreenCanvasSupported,
      isImageDecoderSupported,
      canvasMaxAreaInBytes,
      fontExtraProperties,
      useSystemFonts,
      useWasm,
      useWorkerFetch,
      cMapUrl,
      cMapPacked,
      iccUrl,
      standardFontDataUrl,
      wasmUrl
    }
  };
  const transportParams = {
    ownerDocument,
    pdfBug,
    styleElement,
    rendererWorker: task._rendererWorker,
    enableWebGPU,
    loadingParams: {
      disableAutoFetch,
      enableXfa
    }
  };
  worker.promise.then(function () {
    if (worker.destroyed) {
      throw new Error("Worker was destroyed");
    }
    const workerIdPromise = worker.messageHandler.sendWithPromise("GetDocRequest", docParams, data ? [data.buffer] : null);
    let networkStream;
    if (data) {} else if (rangeTransport) {
      networkStream = new PDFDataTransportStream({
        pdfDataRangeTransport: rangeTransport,
        disableRange,
        disableStream
      });
    } else if (url) {
      const NetworkStream = getNetworkStream(url);
      networkStream = new NetworkStream({
        url,
        httpHeaders,
        withCredentials,
        rangeChunkSize,
        disableRange,
        disableStream
      });
    } else {
      throw new Error("getDocument - expected either `data`, `range`, or `url` parameter.");
    }
    return workerIdPromise.then(workerId => {
      if (worker.destroyed) {
        throw new Error("Worker was destroyed");
      }
      const messageHandler = new MessageHandler(docId, workerId, worker.port);
      const transport = new WorkerTransport(messageHandler, task, networkStream, transportParams, transportFactory, pagesMapper);
      task._transport = transport;
      if (task.destroyed) {
        throw new Error("Loading aborted");
      }
      messageHandler.send("Ready", null);
    });
  }).catch(task._capability.reject).finally(task._setupCapability.resolve);
  return task;
}
class PDFDocumentLoadingTask {
  static #docId = 0;
  _capability = Promise.withResolvers();
  _setupCapability = Promise.withResolvers();
  _transport = null;
  _worker = null;
  _rendererWorker = null;
  docId = `d${PDFDocumentLoadingTask.#docId++}`;
  destroyed = false;
  onPassword = null;
  onProgress = null;
  get promise() {
    return this._capability.promise;
  }
  async destroy() {
    this.destroyed = true;
    this._capability.promise.catch(() => {});
    try {
      if (this._worker?.port) {
        this._worker._pendingDestroy = true;
      }
      await this._setupCapability.promise;
      await this._transport?.destroy();
    } catch (ex) {
      if (this._worker?.port) {
        delete this._worker._pendingDestroy;
      }
      throw ex;
    } finally {
      this._rendererWorker?.destroy();
      this._rendererWorker = null;
    }
    this._transport = null;
    this._worker?.destroy();
    this._worker = null;
  }
  async getData() {
    return this._transport.getData();
  }
}
class PDFDataRangeTransport {
  #capability = Promise.withResolvers();
  #listener = null;
  constructor(length, initialData, progressiveDone = false, contentDispositionFilename = null) {
    this.length = length;
    this.initialData = initialData;
    this.progressiveDone = progressiveDone;
    this.contentDispositionFilename = contentDispositionFilename;
  }
  onDataRange(begin, chunk) {
    this.#listener({
      type: "range",
      begin,
      chunk
    });
  }
  onDataProgressiveRead(chunk) {
    this.#capability.promise.then(() => {
      this.#listener({
        type: "progressiveRead",
        chunk
      });
    });
  }
  onDataProgressiveDone() {
    this.#capability.promise.then(() => {
      this.#listener({
        type: "progressiveDone"
      });
    });
  }
  transportReady(listener) {
    this.#listener = listener;
    this.#capability.resolve();
  }
  requestDataRange(begin, end) {
    unreachable("Abstract method PDFDataRangeTransport.requestDataRange");
  }
  abort() {}
}
class PDFDocumentProxy {
  constructor(pdfInfo, transport) {
    this._pdfInfo = pdfInfo;
    this._transport = transport;
  }
  get pagesMapper() {
    return this._transport.pagesMapper;
  }
  get annotationStorage() {
    return this._transport.annotationStorage;
  }
  get canvasFactory() {
    return this._transport.canvasFactory;
  }
  get filterFactory() {
    return this._transport.filterFactory;
  }
  get numPages() {
    return this._pdfInfo.numPages;
  }
  get fingerprints() {
    return this._pdfInfo.fingerprints;
  }
  get isPureXfa() {
    return shadow(this, "isPureXfa", !!this._transport._htmlForXfa);
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
  getAttachmentContent(id) {
    return this._transport.getAttachmentContent(id);
  }
  getAnnotationsByType(types, pageIndexesToSkip) {
    return this._transport.getAnnotationsByType(types, pageIndexesToSkip);
  }
  getJSActions() {
    return this._transport.getDocJSActions();
  }
  getOutline() {
    return this._transport.getOutline();
  }
  getOptionalContentConfig({
    intent = "display"
  } = {}) {
    const {
      renderingIntent
    } = this._transport.getRenderingIntent(intent);
    return this._transport.getOptionalContentConfig(renderingIntent);
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
  saveDocument(printToPDF) {
    return this._transport.saveDocument(printToPDF);
  }
  extractPages(pageInfos, copyLevels = null) {
    return this._transport.extractPages(pageInfos, copyLevels);
  }
  getDownloadInfo() {
    return this._transport.downloadInfoCapability.promise;
  }
  cleanup(keepLoadedFonts = false) {
    return this._transport.startCleanup(keepLoadedFonts || this.isPureXfa);
  }
  cachedPageNumber(ref) {
    return this._transport.cachedPageNumber(ref);
  }
  get loadingParams() {
    return this._transport.loadingParams;
  }
  get loadingTask() {
    return this._transport.loadingTask;
  }
  getFieldObjects() {
    return this._transport.getFieldObjects();
  }
  getSignatures() {
    return this._transport.getSignatures();
  }
  getSignatureData(id) {
    return this._transport.getSignatureData(id);
  }
  hasJSActions() {
    return this._transport.hasJSActions();
  }
  getCalculationOrderIds() {
    return this._transport.getCalculationOrderIds();
  }
}
class PDFPageProxy {
  #pendingCleanup = false;
  #pagesMapper = null;
  static #idCounter = 0;
  constructor(pageIndex, pageInfo, transport, pagesMapper, pdfBug = false) {
    this._pageIndex = pageIndex;
    this._id = PDFPageProxy.#idCounter++;
    this._pageInfo = pageInfo;
    this._transport = transport;
    this._stats = pdfBug ? new StatTimer() : null;
    this._pdfBug = pdfBug;
    this.commonObjs = transport.commonObjs;
    this.objs = new PDFObjects();
    this._intentStates = new Map();
    this.destroyed = false;
    this.recordedBBoxes = null;
    this.#pagesMapper = pagesMapper;
    this.imageCoordinates = null;
  }
  clone(id) {
    const clone = new PDFPageProxy(id, this._pageInfo, this._transport, this.#pagesMapper, this._pdfBug);
    clone.clonedFromIndex = this.clonedFromIndex ?? this._pageIndex;
    this._transport.updatePage(clone);
    return clone;
  }
  get pageNumber() {
    return this._pageIndex + 1;
  }
  set pageNumber(value) {
    this._pageIndex = value - 1;
    this._transport.updatePage(this);
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
  getViewport({
    scale,
    rotation = this.rotate,
    offsetX = 0,
    offsetY = 0,
    dontFlip = false
  } = {}) {
    return new PageViewport({
      viewBox: this.view,
      userUnit: this.userUnit,
      scale,
      rotation,
      offsetX,
      offsetY,
      dontFlip
    });
  }
  getAnnotations({
    intent = "display"
  } = {}) {
    const {
      renderingIntent
    } = this._transport.getRenderingIntent(intent);
    return this._transport.getAnnotations(this._pageIndex, renderingIntent);
  }
  getJSActions() {
    return this._transport.getPageJSActions(this._pageIndex);
  }
  get filterFactory() {
    return this._transport.filterFactory;
  }
  get isPureXfa() {
    return shadow(this, "isPureXfa", !!this._transport._htmlForXfa);
  }
  async getXfa() {
    return this._transport._htmlForXfa?.children[this._pageIndex] || null;
  }
  render({
    canvasContext,
    canvas = canvasContext.canvas,
    viewport,
    intent = "display",
    annotationMode = AnnotationMode.ENABLE,
    transform = null,
    background = null,
    optionalContentConfigPromise = null,
    annotationCanvasMap = null,
    pageColors = null,
    printAnnotationStorage = null,
    isEditing = false,
    recordImages = false,
    recordOperations = false,
    partialFrames = false,
    operationsFilter = null
  }) {
    this._stats?.time("Overall");
    const intentArgs = this._transport.getRenderingIntent(intent, annotationMode, printAnnotationStorage, isEditing);
    const {
      renderingIntent,
      cacheKey
    } = intentArgs;
    this.#pendingCleanup = false;
    optionalContentConfigPromise ||= this._transport.getOptionalContentConfig(renderingIntent);
    const intentState = this._intentStates.getOrInsertComputed(cacheKey, makeObj);
    if (intentState.streamReaderCancelTimeout) {
      clearTimeout(intentState.streamReaderCancelTimeout);
      intentState.streamReaderCancelTimeout = null;
    }
    const intentPrint = !!(renderingIntent & RenderingIntentFlag.PRINT);
    if (!intentState.displayReadyCapability) {
      intentState.displayReadyCapability = Promise.withResolvers();
      intentState.operatorList = {
        fnArray: [],
        argsArray: [],
        lastChunk: false,
        separateAnnots: null
      };
      this._stats?.time("Page Request");
      this._pumpOperatorList(intentArgs);
    }
    const recordForDebugger = !!(this._pdfBug && globalThis.StepperManager?.enabled);
    const shouldRecordOperations = !!canvas && !this.recordedBBoxes && (recordOperations || recordForDebugger);
    const shouldRecordImages = !!canvas && !this.imageCoordinates && recordImages;
    const complete = error => {
      intentState.renderTasks.delete(internalRenderTask);
      if (shouldRecordOperations) {
        const {
          recordedBBoxes
        } = internalRenderTask;
        if (recordedBBoxes) {
          internalRenderTask.stepper?.setOperatorBBoxes(recordedBBoxes, internalRenderTask.debugMetadata);
          if (recordOperations) {
            this.recordedBBoxes = recordedBBoxes;
          }
        }
      }
      if (shouldRecordImages && !error) {
        this.imageCoordinates = internalRenderTask.imageCoordinates;
      }
      if (intentPrint) {
        this.#pendingCleanup = true;
      }
      this.#tryCleanup();
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
        if (globalThis.Stats?.enabled) {
          globalThis.Stats.add(this.pageNumber, this._stats);
        }
      }
    };
    const internalRenderTask = new InternalRenderTask({
      callback: complete,
      params: {
        canvas,
        canvasContext,
        viewport,
        transform,
        background,
        recordOperations: shouldRecordOperations,
        recordImages: shouldRecordImages,
        partialFrames,
        recordForDebugger
      },
      objs: this.objs,
      commonObjs: this.commonObjs,
      annotationCanvasMap,
      operatorList: intentState.operatorList,
      pageIndex: this._pageIndex,
      pageProxyId: this._id,
      canvasFactory: this._transport.canvasFactory,
      filterFactory: this._transport.filterFactory,
      useRequestAnimationFrame: !intentPrint,
      pdfBug: this._pdfBug,
      pageColors,
      operationsFilter,
      rendererWorker: this._transport.rendererWorker,
      waitForGPU: () => this._transport.waitForGPU()
    });
    (intentState.renderTasks ||= new Set()).add(internalRenderTask);
    const renderTask = internalRenderTask.task;
    Promise.all([intentState.displayReadyCapability.promise, optionalContentConfigPromise]).then(async ([transparency, optionalContentConfig]) => {
      if (this.destroyed) {
        complete();
        return;
      }
      this._stats?.time("Rendering");
      if (!(optionalContentConfig.renderingIntent & renderingIntent)) {
        throw new Error("Must use the same `intent`-argument when calling the `PDFPageProxy.render` " + "and `PDFDocumentProxy.getOptionalContentConfig` methods.");
      }
      await internalRenderTask.initializeGraphics({
        transparency,
        optionalContentConfig
      });
      internalRenderTask.operatorListChanged();
    }).catch(complete);
    return renderTask;
  }
  getOperatorList({
    intent = "display",
    annotationMode = AnnotationMode.ENABLE,
    printAnnotationStorage = null,
    isEditing = false
  } = {}) {
    function operatorListChanged() {
      if (intentState.operatorList.lastChunk) {
        intentState.opListReadCapability.resolve(intentState.operatorList);
        intentState.renderTasks.delete(opListTask);
      }
    }
    const intentArgs = this._transport.getRenderingIntent(intent, annotationMode, printAnnotationStorage, isEditing, true);
    const intentState = this._intentStates.getOrInsertComputed(intentArgs.cacheKey, makeObj);
    let opListTask;
    if (!intentState.opListReadCapability) {
      opListTask = Object.create(null);
      opListTask.operatorListChanged = operatorListChanged;
      intentState.opListReadCapability = Promise.withResolvers();
      (intentState.renderTasks ||= new Set()).add(opListTask);
      intentState.operatorList = {
        fnArray: [],
        argsArray: [],
        lastChunk: false,
        separateAnnots: null
      };
      this._stats?.time("Page Request");
      this._pumpOperatorList(intentArgs);
    }
    return intentState.opListReadCapability.promise;
  }
  streamTextContent({
    includeMarkedContent = false,
    disableNormalization = false
  } = {}) {
    const TEXT_CONTENT_CHUNK_SIZE = 100;
    return this._transport.messageHandler.sendWithStream("GetTextContent", {
      pageId: this.#pagesMapper.getPageId(this._pageIndex + 1) - 1,
      pageIndex: this._pageIndex,
      includeMarkedContent: includeMarkedContent === true,
      disableNormalization: disableNormalization === true
    }, {
      highWaterMark: TEXT_CONTENT_CHUNK_SIZE,
      size: textContent => textContent.items.length
    });
  }
  async getTextContent(params = {}) {
    if (this._transport._htmlForXfa) {
      return this.getXfa().then(xfa => XfaText.textContent(xfa));
    }
    const readableStream = this.streamTextContent(params);
    const reader = readableStream.getReader();
    const textContent = {
      items: [],
      styles: Object.create(null),
      lang: null
    };
    while (true) {
      const {
        value,
        done
      } = await reader.read();
      if (done) {
        break;
      }
      textContent.lang ??= value.lang;
      Object.assign(textContent.styles, value.styles);
      textContent.items.push(...value.items);
    }
    return textContent;
  }
  getStructTree() {
    return this._transport.getStructTree(this._pageIndex);
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
    this._transport.cleanupPage(this._id);
    this.#pendingCleanup = false;
    return Promise.all(waitOn);
  }
  cleanup(resetStats = false) {
    this.#pendingCleanup = true;
    const success = this.#tryCleanup();
    if (resetStats && success) {
      this._stats &&= new StatTimer();
    }
    return success;
  }
  #tryCleanup() {
    if (!this.#pendingCleanup || this.destroyed) {
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
    this._transport.cleanupPage(this._id);
    this.#pendingCleanup = false;
    return true;
  }
  _startRenderPage(transparency, cacheKey) {
    const intentState = this._intentStates.get(cacheKey);
    if (!intentState) {
      return;
    }
    this._stats?.timeEnd("Page Request");
    intentState.displayReadyCapability?.resolve(transparency);
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
      this.#tryCleanup();
    }
  }
  _pumpOperatorList({
    renderingIntent,
    cacheKey,
    annotationStorageSerializable,
    modifiedIds
  }) {
    const {
      map,
      transfer
    } = annotationStorageSerializable;
    const readableStream = this._transport.messageHandler.sendWithStream("GetOperatorList", {
      pageId: this.#pagesMapper.getPageId(this._pageIndex + 1) - 1,
      pageIndex: this._pageIndex,
      pageProxyId: this._id,
      intent: renderingIntent,
      cacheKey,
      annotationStorage: map,
      modifiedIds
    }, undefined, transfer);
    const reader = readableStream.getReader();
    const intentState = this._intentStates.get(cacheKey);
    intentState.streamReader = reader;
    const pump = () => {
      reader.read().then(({
        value,
        done
      }) => {
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
          this.#tryCleanup();
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
  _abortOperatorList({
    intentState,
    reason,
    force = false
  }) {
    if (!intentState.streamReader) {
      return;
    }
    if (intentState.streamReaderCancelTimeout) {
      clearTimeout(intentState.streamReaderCancelTimeout);
      intentState.streamReaderCancelTimeout = null;
    }
    if (!force) {
      if (intentState.renderTasks.size > 0) {
        return;
      }
      if (reason instanceof RenderingCancelledException) {
        let delay = RENDERING_CANCELLED_TIMEOUT;
        if (reason.extraDelay > 0 && reason.extraDelay < 1000) {
          delay += reason.extraDelay;
        }
        intentState.streamReaderCancelTimeout = setTimeout(() => {
          intentState.streamReaderCancelTimeout = null;
          this._abortOperatorList({
            intentState,
            reason,
            force: true
          });
        }, delay);
        return;
      }
    }
    intentState.streamReader.cancel(new AbortException(reason.message)).catch(() => {});
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
class PDFWorker {
  #capability = Promise.withResolvers();
  #messageHandler = null;
  #port = null;
  #webWorker = null;
  static #fakeWorkerId = 0;
  static #isWorkerDisabled = false;
  static #workerPorts = new WeakMap();
  static {
    if (isNodeJS) {
      this.#isWorkerDisabled = true;
      GlobalWorkerOptions.workerSrc ||= "./pdf.worker.mjs";
    }
  }
  constructor({
    name = null,
    port = null,
    verbosity = getVerbosityLevel()
  } = {}) {
    this.name = name;
    this.destroyed = false;
    this.verbosity = verbosity;
    if (port) {
      if (PDFWorker.#workerPorts.has(port)) {
        throw new Error("Cannot use more than one PDFWorker per port.");
      }
      PDFWorker.#workerPorts.set(port, this);
      this.#initializeFromPort(port);
    } else {
      this.#initialize();
    }
  }
  get promise() {
    return this.#capability.promise;
  }
  #resolve() {
    this.#capability.resolve();
    this.#messageHandler.send("configure", {
      verbosity: this.verbosity
    });
  }
  get port() {
    return this.#port;
  }
  get messageHandler() {
    return this.#messageHandler;
  }
  #initializeFromPort(port) {
    this.#port = port;
    this.#messageHandler = new MessageHandler("main", "worker", port);
    this.#messageHandler.on("ready", () => {});
    this.#resolve();
  }
  #initialize() {
    if (PDFWorker.#isWorkerDisabled || PDFWorker.#mainThreadWorkerMessageHandler) {
      this.#setupFakeWorker();
      return;
    }
    const {
      workerSrc
    } = PDFWorker;
    try {
      const worker = new Worker(getWorkerSrc(workerSrc), {
        type: "module"
      });
      const messageHandler = new MessageHandler("main", "worker", worker);
      const terminateEarly = () => {
        ac.abort();
        messageHandler.destroy();
        worker.terminate();
        if (this.destroyed) {
          this.#capability.reject(new Error("Worker was destroyed"));
        } else {
          this.#setupFakeWorker();
        }
      };
      const ac = new AbortController();
      worker.addEventListener("error", () => {
        if (!this.#webWorker) {
          terminateEarly();
        }
      }, {
        signal: ac.signal
      });
      messageHandler.on("ready", data => {
        ac.abort();
        if (this.destroyed || !(data instanceof Uint8Array)) {
          terminateEarly();
          return;
        }
        this.#messageHandler = messageHandler;
        this.#port = worker;
        this.#webWorker = worker;
        this.#resolve();
      });
    } catch {
      info("The worker has been disabled.");
      this.#setupFakeWorker();
    }
  }
  #setupFakeWorker() {
    if (!PDFWorker.#isWorkerDisabled) {
      warn("Setting up fake worker.");
      PDFWorker.#isWorkerDisabled = true;
    }
    PDFWorker._setupFakeWorkerGlobal.then(WorkerMessageHandler => {
      if (this.destroyed) {
        this.#capability.reject(new Error("Worker was destroyed"));
        return;
      }
      const port = new LoopbackPort();
      this.#port = port;
      const id = `fake${PDFWorker.#fakeWorkerId++}`;
      const workerHandler = new MessageHandler(id + "_worker", id, port);
      WorkerMessageHandler.setup(workerHandler, port);
      this.#messageHandler = new MessageHandler(id, id + "_worker", port);
      this.#resolve();
    }).catch(reason => {
      this.#capability.reject(new Error(`Setting up fake worker failed: "${reason.message}".`));
    });
  }
  destroy() {
    this.destroyed = true;
    this.#webWorker?.terminate();
    this.#webWorker = null;
    PDFWorker.#workerPorts.delete(this.#port);
    this.#port = null;
    this.#messageHandler?.destroy();
    this.#messageHandler = null;
  }
  static create(params) {
    const cachedPort = this.#workerPorts.get(params?.port);
    if (cachedPort) {
      if (cachedPort._pendingDestroy) {
        throw new Error("PDFWorker.create - the worker is being destroyed.\n" + "Please remember to await `PDFDocumentLoadingTask.destroy()`-calls.");
      }
      return cachedPort;
    }
    return new PDFWorker(params);
  }
  static get workerSrc() {
    if (GlobalWorkerOptions.workerSrc) {
      return GlobalWorkerOptions.workerSrc;
    }
    throw new Error('No "GlobalWorkerOptions.workerSrc" specified.');
  }
  static get #mainThreadWorkerMessageHandler() {
    try {
      return globalThis.pdfjsWorker?.WorkerMessageHandler || null;
    } catch {
      return null;
    }
  }
  static get _setupFakeWorkerGlobal() {
    const loader = async () => {
      if (this.#mainThreadWorkerMessageHandler) {
        return this.#mainThreadWorkerMessageHandler;
      }
      const worker = await import(
      /*webpackIgnore: true*/
      /*@vite-ignore*/
      this.workerSrc);
      return worker.WorkerMessageHandler;
    };
    return shadow(this, "_setupFakeWorkerGlobal", loader());
  }
}
class WorkerTransport {
  downloadInfoCapability = Promise.withResolvers();
  #fullReader = null;
  #hasMeshPattern = false;
  #methodPromises = new Map();
  #networkStream = null;
  #pageCache = new Map();
  #pagePromises = new Map();
  #pageRefCache = new Map();
  #passwordCapability = null;
  #printToPDF = null;
  constructor(messageHandler, loadingTask, networkStream, params, factory, pagesMapper) {
    this.messageHandler = messageHandler;
    this.loadingTask = loadingTask;
    this.#networkStream = networkStream;
    this.commonObjs = new PDFObjects();
    this.fontLoader = new FontLoader({
      ownerDocument: params.ownerDocument,
      styleElement: params.styleElement
    });
    this.rendererWorker = params.rendererWorker;
    this.loadingParams = params.loadingParams;
    this._params = params;
    this.canvasFactory = factory.canvasFactory;
    this.filterFactory = factory.filterFactory;
    this.binaryDataFactory = factory.binaryDataFactory;
    this.pagesMapper = pagesMapper;
    this.destroyed = false;
    this.destroyCapability = null;
    this.setupMessageHandler();
  }
  updatePage(page) {
    this.#pageCache.set(page._id, page);
    this.#pagePromises.set(page._pageIndex, Promise.resolve(page));
  }
  #cacheSimpleMethod(name, data = null) {
    return this.#methodPromises.getOrInsertComputed(name, () => this.messageHandler.sendWithPromise(name, data));
  }
  #onProgress({
    loaded,
    total
  }) {
    this.loadingTask.onProgress?.({
      loaded,
      total,
      percent: total ? MathClamp(Math.round(loaded / total * 100), 0, 100) : NaN
    });
  }
  get annotationStorage() {
    return shadow(this, "annotationStorage", new AnnotationStorage());
  }
  getRenderingIntent(intent, annotationMode = AnnotationMode.ENABLE, printAnnotationStorage = null, isEditing = false, isOpList = false) {
    let renderingIntent = RenderingIntentFlag.DISPLAY;
    let annotationStorageSerializable = SerializableEmpty;
    switch (intent) {
      case "any":
        renderingIntent = RenderingIntentFlag.ANY;
        break;
      case "display":
        break;
      case "print":
        renderingIntent = RenderingIntentFlag.PRINT;
        break;
      default:
        warn(`getRenderingIntent - invalid intent: ${intent}`);
    }
    const annotationStorage = renderingIntent & RenderingIntentFlag.PRINT && printAnnotationStorage instanceof PrintAnnotationStorage ? printAnnotationStorage : this.annotationStorage;
    switch (annotationMode) {
      case AnnotationMode.DISABLE:
        renderingIntent += RenderingIntentFlag.ANNOTATIONS_DISABLE;
        break;
      case AnnotationMode.ENABLE:
        break;
      case AnnotationMode.ENABLE_FORMS:
        renderingIntent += RenderingIntentFlag.ANNOTATIONS_FORMS;
        break;
      case AnnotationMode.ENABLE_STORAGE:
        renderingIntent += RenderingIntentFlag.ANNOTATIONS_STORAGE;
        annotationStorageSerializable = annotationStorage.serializable;
        break;
      default:
        warn(`getRenderingIntent - invalid annotationMode: ${annotationMode}`);
    }
    if (isEditing) {
      renderingIntent += RenderingIntentFlag.IS_EDITING;
    }
    if (isOpList) {
      renderingIntent += RenderingIntentFlag.OPLIST;
    }
    const {
      ids: modifiedIds,
      hash: modifiedIdsHash
    } = annotationStorage.modifiedIds;
    const cacheKeyBuf = [renderingIntent, annotationStorageSerializable.hash, modifiedIdsHash];
    return {
      renderingIntent,
      cacheKey: cacheKeyBuf.join("_"),
      annotationStorageSerializable,
      modifiedIds
    };
  }
  destroy() {
    if (this.destroyCapability) {
      return this.destroyCapability.promise;
    }
    this.destroyed = true;
    this.destroyCapability = Promise.withResolvers();
    this.#passwordCapability?.reject(new Error("Worker was destroyed during onPassword callback"));
    const waitOn = [];
    for (const page of this.#pageCache.values()) {
      waitOn.push(page._destroy());
    }
    this.#pageCache.clear();
    this.#pagePromises.clear();
    this.#pageRefCache.clear();
    if (Object.hasOwn(this, "annotationStorage")) {
      this.annotationStorage.resetModified();
    }
    const terminated = this.messageHandler.sendWithPromise("Terminate", null);
    waitOn.push(terminated);
    Promise.all(waitOn).then(() => {
      this.commonObjs.clear();
      this.fontLoader.clear();
      this.#methodPromises.clear();
      this.filterFactory.destroy();
      TextLayer.cleanup();
      this.#networkStream?.cancelAllRequests(new AbortException("Worker was terminated."));
      this.messageHandler?.destroy();
      this.messageHandler = null;
      this.rendererWorker = null;
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
      assert(this.#networkStream, "GetReader - no `BasePDFStream` instance available.");
      this.#fullReader = this.#networkStream.getFullReader();
      this.#fullReader.onProgress = evt => this.#onProgress(evt);
      sink.onPull = () => {
        this.#fullReader.read().then(function ({
          value,
          done
        }) {
          if (done) {
            sink.close();
            return;
          }
          assert(value instanceof ArrayBuffer, "GetReader - expected an ArrayBuffer.");
          sink.enqueue(new Uint8Array(value), 1, [value]);
        }).catch(reason => {
          sink.error(reason);
        });
      };
      sink.onCancel = reason => {
        this.#fullReader.cancel(reason);
        sink.ready.catch(readyReason => {
          if (this.destroyed) {
            return;
          }
          throw readyReason;
        });
      };
    });
    messageHandler.on("ReaderHeadersReady", async data => {
      await this.#fullReader.headersReady;
      const {
        isStreamingSupported,
        isRangeSupported,
        contentLength
      } = this.#fullReader;
      if (isStreamingSupported && isRangeSupported) {
        this.#fullReader.onProgress = null;
      }
      return {
        isStreamingSupported,
        isRangeSupported,
        contentLength
      };
    });
    messageHandler.on("GetRangeReader", (data, sink) => {
      assert(this.#networkStream, "GetRangeReader - no `BasePDFStream` instance available.");
      const rangeReader = this.#networkStream.getRangeReader(data.begin, data.end);
      if (!rangeReader) {
        sink.close();
        return;
      }
      sink.onPull = () => {
        rangeReader.read().then(function ({
          value,
          done
        }) {
          if (done) {
            sink.close();
            return;
          }
          assert(value instanceof ArrayBuffer, "GetRangeReader - expected an ArrayBuffer.");
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
    messageHandler.on("GetDoc", ({
      pdfInfo
    }) => {
      this.pagesMapper.pagesNumber = pdfInfo.numPages;
      this._numPages = pdfInfo.numPages;
      this._htmlForXfa = pdfInfo.htmlForXfa;
      delete pdfInfo.htmlForXfa;
      loadingTask._capability.resolve(new PDFDocumentProxy(pdfInfo, this));
    });
    messageHandler.on("DocException", ex => {
      loadingTask._capability.reject(wrapReason(ex));
    });
    messageHandler.on("PasswordRequest", ex => {
      this.#passwordCapability = Promise.withResolvers();
      try {
        if (!loadingTask.onPassword) {
          throw wrapReason(ex);
        }
        const updatePassword = password => {
          if (password instanceof Error) {
            this.#passwordCapability.reject(password);
          } else {
            this.#passwordCapability.resolve({
              password
            });
          }
        };
        loadingTask.onPassword(updatePassword, ex.code);
      } catch (err) {
        this.#passwordCapability.reject(err);
      }
      return this.#passwordCapability.promise;
    });
    messageHandler.on("DataLoaded", data => {
      this.#onProgress({
        loaded: data.length,
        total: data.length
      });
      this.downloadInfoCapability.resolve(data);
    });
    messageHandler.on("StartRenderPage", data => {
      if (this.destroyed) {
        return;
      }
      const page = this.#pageCache.get(data.pageProxyId);
      page._startRenderPage(data.transparency, data.cacheKey);
    });
    const objectHandler = new ObjectHandler({
      messageHandler,
      commonObjs: this.commonObjs,
      fontLoader: this.fontLoader,
      pageCache: this.#pageCache,
      pdfBug: this._params.pdfBug
    });
    this.rendererWorker?.promise.then(() => {
      this.rendererWorker?.messageHandler?.on("FontFallback", data => this.destroyed ? null : messageHandler.sendWithPromise("FontFallback", data));
    }, () => {});
    messageHandler.on("commonobj", ([id, type, exportedData]) => {
      if (this.destroyed) {
        return null;
      }
      const {
        rendererWorker
      } = this;
      if (type === "CopyLocalImage") {
        if (this.commonObjs.has(id)) {
          return null;
        }
        const dataLen = objectHandler.resolveCommonObject(id, type, exportedData);
        if (dataLen) {
          rendererWorker?.sendCommonObj(id, "Image", this.commonObjs.get(id));
        }
        return dataLen;
      }
      rendererWorker?.sendCommonObj(id, type, exportedData);
      if (!this.commonObjs.has(id)) {
        objectHandler.resolveCommonObject(id, type, exportedData);
        if (type === "Pattern" && this.commonObjs.get(id)[0] === "Mesh") {
          this.#hasMeshPattern = true;
        }
      }
      return null;
    });
    messageHandler.on("obj", ([id, pageProxyId, type, imageData]) => {
      if (this.destroyed) {
        return;
      }
      if (type === "Pattern" && imageData[0] === "Mesh") {
        this.#hasMeshPattern = true;
      }
      if (objectHandler.resolveObject(id, pageProxyId, type, imageData)) {
        this.rendererWorker?.sendObj(id, pageProxyId, type, imageData);
      }
    });
    messageHandler.on("DocProgress", data => {
      if (this.destroyed) {
        return;
      }
      this.#onProgress(data);
    });
    messageHandler.on("FetchBinaryData", async data => {
      if (this.destroyed) {
        throw new Error("Worker was destroyed.");
      }
      if (!this.binaryDataFactory) {
        throw new Error("`BinaryDataFactory` not initialized, see the `useWorkerFetch` parameter.");
      }
      return this.binaryDataFactory.fetch(data);
    });
  }
  getData() {
    return this.messageHandler.sendWithPromise("GetData", null);
  }
  saveDocument(printToPDF = null) {
    if (this.annotationStorage.size <= 0) {
      warn("saveDocument called while `annotationStorage` is empty, " + "please use the getData-method instead.");
    }
    const {
      map,
      transfer
    } = this.annotationStorage.serializable;
    return this.messageHandler.sendWithPromise("SaveDocument", {
      isPureXfa: !!this._htmlForXfa,
      numPages: this._numPages,
      annotationStorage: map,
      supportsPrintToPDF: this.#printToPDF !== null,
      filename: this.#fullReader?.filename ?? null
    }, transfer).finally(() => {
      this.#printToPDF = null;
      this.annotationStorage.resetModified();
    });
  }
  extractPages(pageInfos, copyLevels = null) {
    const params = {
      pageInfos
    };
    let transfer;
    const ImageBitmapCtor = globalThis.ImageBitmap;
    if (typeof ImageBitmapCtor === "function") {
      const infos = Array.isArray(pageInfos) ? pageInfos : [pageInfos];
      for (const pageInfo of infos) {
        if (pageInfo?.image instanceof ImageBitmapCtor) {
          (transfer ||= []).push(pageInfo.image);
        }
      }
    }
    if (this.annotationStorage.size > 0) {
      const serialized = this.annotationStorage.serializable;
      let {
        map
      } = serialized;
      if (serialized.transfer?.length) {
        if (transfer) {
          transfer.push(...serialized.transfer);
        } else {
          transfer = serialized.transfer;
        }
      }
      const mapping = this.pagesMapper.getMapping();
      if (mapping) {
        const remapped = new Map();
        for (const [k, v] of map) {
          if (v?.pageIndex !== undefined && v.pageIndex >= 0 && v.pageIndex < mapping.length) {
            const copyLevel = copyLevels?.[v.pageIndex] ?? 0;
            const sourceIdx = mapping[v.pageIndex] - 1;
            if (sourceIdx !== v.pageIndex || copyLevel !== 0) {
              remapped.set(k, {
                ...v,
                pageIndex: sourceIdx,
                copyLevel
              });
              continue;
            }
          }
          remapped.set(k, v);
        }
        map = remapped;
      }
      params.annotationStorage = map;
    }
    return this.messageHandler.sendWithPromise("ExtractPages", params, transfer).finally(() => {
      this.annotationStorage.resetModified();
    });
  }
  waitForGPU() {
    return this._params.enableWebGPU && this.#hasMeshPattern && !isGPUReady() ? initGPU() : null;
  }
  getPage(pageNumber) {
    if (!Number.isInteger(pageNumber) || pageNumber <= 0 || pageNumber > this.pagesMapper.pagesNumber) {
      return Promise.reject(new Error("Invalid page request."));
    }
    const pageIndex = pageNumber - 1;
    const newPageIndex = this.pagesMapper.getPageId(pageNumber) - 1;
    const cachedPromise = this.#pagePromises.get(pageIndex);
    if (cachedPromise) {
      return cachedPromise;
    }
    const promise = this.messageHandler.sendWithPromise("GetPage", {
      pageIndex: newPageIndex
    }).then(pageInfo => {
      if (this.destroyed) {
        throw new Error("Transport destroyed");
      }
      if (pageInfo.refStr) {
        this.#pageRefCache.set(pageInfo.refStr, newPageIndex);
      }
      const page = new PDFPageProxy(pageIndex, pageInfo, this, this.pagesMapper, this._params.pdfBug);
      this.#pageCache.set(page._id, page);
      return page;
    });
    this.#pagePromises.set(pageIndex, promise);
    return promise;
  }
  async getPageIndex(ref) {
    if (!isRefProxy(ref)) {
      throw new Error("Invalid pageIndex request.");
    }
    const index = await this.messageHandler.sendWithPromise("GetPageIndex", {
      num: ref.num,
      gen: ref.gen
    });
    const pageNumber = this.pagesMapper.getPageNumber(index + 1);
    if (pageNumber === 0) {
      throw new Error("GetPageIndex: page has been removed.");
    }
    return pageNumber - 1;
  }
  getAnnotations(pageIndex, intent) {
    return this.messageHandler.sendWithPromise("GetAnnotations", {
      pageIndex: this.pagesMapper.getPageId(pageIndex + 1) - 1,
      intent
    });
  }
  getFieldObjects() {
    return this.#cacheSimpleMethod("GetFieldObjects");
  }
  getSignatures() {
    return this.#cacheSimpleMethod("GetSignatures");
  }
  getSignatureData(id) {
    return this.messageHandler.sendWithPromise("GetSignatureData", id);
  }
  hasJSActions() {
    return this.#cacheSimpleMethod("HasJSActions");
  }
  getCalculationOrderIds() {
    return this.messageHandler.sendWithPromise("GetCalculationOrderIds", null);
  }
  getDestinations() {
    return this.messageHandler.sendWithPromise("GetDestinations", null);
  }
  getDestination(id) {
    return typeof id !== "string" ? Promise.reject(new Error("Invalid destination request.")) : this.messageHandler.sendWithPromise("GetDestination", {
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
  getAttachmentContent(id) {
    return this.messageHandler.sendWithPromise("GetAttachmentContent", id);
  }
  getAnnotationsByType(types, pageIndexesToSkip) {
    return this.messageHandler.sendWithPromise("GetAnnotationsByType", {
      types,
      pageIndexesToSkip
    });
  }
  getDocJSActions() {
    return this.#cacheSimpleMethod("GetDocJSActions");
  }
  getPageJSActions(pageIndex) {
    return this.messageHandler.sendWithPromise("GetPageJSActions", {
      pageIndex: this.pagesMapper.getPageId(pageIndex + 1) - 1
    });
  }
  getStructTree(pageIndex) {
    return this.messageHandler.sendWithPromise("GetStructTree", {
      pageIndex: this.pagesMapper.getPageId(pageIndex + 1) - 1
    });
  }
  getOutline() {
    return this.messageHandler.sendWithPromise("GetOutline", null);
  }
  getOptionalContentConfig(renderingIntent) {
    const name = "GetOptionalContentConfig";
    return this.#methodPromises.getOrInsertComputed(name, () => this.messageHandler.sendWithPromise(name, null).catch(reason => {
      warn(`${name}: "${reason}".`);
      return null;
    })).then(data => new OptionalContentConfig(data, renderingIntent));
  }
  getPermissions() {
    return this.messageHandler.sendWithPromise("GetPermissions", null);
  }
  getMetadata() {
    const name = "GetMetadata";
    return this.#methodPromises.getOrInsertComputed(name, () => this.messageHandler.sendWithPromise(name, null).then(results => ({
      info: results[0],
      metadata: results[1] ? new Metadata(results[1]) : null,
      contentDispositionFilename: this.#fullReader?.filename ?? null,
      contentLength: this.#fullReader?.contentLength ?? null,
      hasStructTree: results[2]
    })));
  }
  getMarkInfo() {
    return this.messageHandler.sendWithPromise("GetMarkInfo", null);
  }
  async startCleanup(keepLoadedFonts = false) {
    if (this.destroyed) {
      return;
    }
    await this.messageHandler.sendWithPromise("Cleanup", null);
    for (const page of this.#pageCache.values()) {
      const cleanupSuccessful = page.cleanup();
      if (!cleanupSuccessful) {
        throw new Error(`startCleanup: Page ${page.pageNumber} is currently rendering.`);
      }
    }
    this.commonObjs.clear();
    if (!keepLoadedFonts) {
      this.fontLoader.clear();
    }
    this.rendererWorker?.cleanup(keepLoadedFonts);
    this.#methodPromises.clear();
    this.filterFactory.destroy(true);
    TextLayer.cleanup();
  }
  cleanupPage(pageProxyId) {
    if (!this.destroyed) {
      this.messageHandler.send("CleanupPage", {
        pageProxyId
      });
    }
    this.rendererWorker?.cleanupPage(pageProxyId);
  }
  cachedPageNumber(ref) {
    if (!isRefProxy(ref)) {
      return null;
    }
    const refStr = ref.gen === 0 ? `${ref.num}R` : `${ref.num}R${ref.gen}`;
    const pageIndex = this.#pageRefCache.get(refStr);
    if (pageIndex >= 0) {
      const pageNumber = this.pagesMapper.getPageNumber(pageIndex + 1);
      if (pageNumber !== 0) {
        return pageNumber;
      }
    }
    return null;
  }
}
class RenderTask {
  _internalRenderTask = null;
  onContinue = null;
  onError = null;
  onFrame = null;
  constructor(internalRenderTask) {
    this._internalRenderTask = internalRenderTask;
  }
  get promise() {
    return this._internalRenderTask.capability.promise;
  }
  cancel(extraDelay = 0) {
    this._internalRenderTask.cancel(null, extraDelay);
  }
  get separateAnnots() {
    const {
      separateAnnots
    } = this._internalRenderTask.operatorList;
    if (!separateAnnots) {
      return false;
    }
    const {
      annotationCanvasMap
    } = this._internalRenderTask;
    return separateAnnots.form || separateAnnots.canvas && annotationCanvasMap?.size > 0;
  }
  get imageCoordinates() {
    return this._internalRenderTask.imageCoordinates || null;
  }
  get isWorkerRendering() {
    return this._internalRenderTask.isWorkerRendering;
  }
}
class InternalRenderTask {
  #dependencyTracker = null;
  #imagesTracker = null;
  #rAF = null;
  #rendererTask = null;
  #waitForGPU = null;
  static #canvasInUse = new WeakSet();
  constructor({
    callback,
    params,
    objs,
    commonObjs,
    annotationCanvasMap,
    operatorList,
    pageIndex,
    pageProxyId,
    canvasFactory,
    filterFactory,
    useRequestAnimationFrame = false,
    pdfBug = false,
    pageColors = null,
    operationsFilter = null,
    rendererWorker = null,
    waitForGPU = null
  }) {
    this.callback = callback;
    this.params = params;
    this.objs = objs;
    this.commonObjs = commonObjs;
    this.annotationCanvasMap = annotationCanvasMap;
    this.operatorListIdx = null;
    this.operatorList = operatorList;
    this._pageIndex = pageIndex;
    this.canvasFactory = canvasFactory;
    this.filterFactory = filterFactory;
    this._pdfBug = pdfBug;
    this.pageColors = pageColors;
    this.running = false;
    this.graphicsReadyCallback = null;
    this.graphicsReady = false;
    this._useRequestAnimationFrame = useRequestAnimationFrame === true && typeof window !== "undefined";
    this.cancelled = false;
    this.capability = Promise.withResolvers();
    this.task = new RenderTask(this);
    this._cancelBound = this.cancel.bind(this);
    this._continueBound = this._continue.bind(this);
    this._scheduleNextBound = this._scheduleNext.bind(this);
    this._nextBound = this._next.bind(this);
    this._canvas = params.canvas;
    this._canvasContext = params.canvas ? null : params.canvasContext;
    this._operationsFilter = operationsFilter;
    this.#waitForGPU = waitForGPU;
    this.#rendererTask = rendererWorker?.createRenderTask({
      pageProxyId,
      operatorList,
      params,
      pageColors,
      canvasFactory,
      annotationCanvasMap,
      onFrame: () => this.task.onFrame?.(),
      onError: reason => this.cancel(reason)
    }) ?? null;
  }
  get completed() {
    return this.capability.promise.catch(() => {});
  }
  get isWorkerRendering() {
    return !!this.#rendererTask;
  }
  get imageCoordinates() {
    return this.#rendererTask ? this.#rendererTask.imageCoordinates : this.#imagesTracker?.take();
  }
  get recordedBBoxes() {
    return this.#rendererTask ? this.#rendererTask.recordedBBoxes : this.#dependencyTracker?.take();
  }
  get debugMetadata() {
    return this.#dependencyTracker?.takeDebugMetadata() ?? null;
  }
  async initializeGraphics({
    transparency = false,
    optionalContentConfig
  }) {
    if (this.cancelled) {
      return;
    }
    if (this._canvas) {
      if (InternalRenderTask.#canvasInUse.has(this._canvas)) {
        throw new Error("Cannot use the same canvas during multiple render() operations. " + "Use different canvas or ensure previous operations were " + "cancelled or completed.");
      }
      InternalRenderTask.#canvasInUse.add(this._canvas);
    }
    if (this._pdfBug && globalThis.StepperManager?.enabled) {
      this.stepper = globalThis.StepperManager.create(this._pageIndex);
      this.stepper.init(this.operatorList);
      this.stepper.nextBreakPoint = this.stepper.getNextBreakPoint();
    }
    if (this.#rendererTask) {
      const initialized = await this.#rendererTask.initialize(transparency, optionalContentConfig);
      if (this.cancelled) {
        return;
      }
      if (!initialized) {
        this.#rendererTask = null;
      }
    }
    if (!this.#rendererTask) {
      const {
        viewport,
        transform,
        background,
        recordOperations,
        recordImages,
        recordForDebugger
      } = this.params;
      const canvasContext = this._canvasContext || this.canvasFactory.getNoAlphaContext(this._canvas);
      const {
        dependencyTracker,
        imagesTracker
      } = createCanvasTrackers(this._canvas, this.operatorList.fnArray.length, {
        recordOperations,
        recordImages,
        recordDebugMetadata: recordForDebugger
      });
      this.#dependencyTracker = dependencyTracker;
      this.#imagesTracker = imagesTracker;
      this.gfx = new CanvasGraphics(canvasContext, this.commonObjs, this.objs, this.canvasFactory, this.filterFactory, {
        optionalContentConfig
      }, this.annotationCanvasMap, this.pageColors, dependencyTracker, imagesTracker);
      this.gfx.beginDrawing({
        transform,
        viewport,
        transparency,
        background
      });
    }
    this.operatorListIdx = 0;
    this.graphicsReady = true;
    this.graphicsReadyCallback?.();
  }
  cancel(error = null, extraDelay = 0) {
    this.running = false;
    this.cancelled = true;
    this.#rendererTask?.cancel();
    this.gfx?.endDrawing();
    if (this.#rAF) {
      window.cancelAnimationFrame(this.#rAF);
      this.#rAF = null;
    }
    InternalRenderTask.#canvasInUse.delete(this._canvas);
    error ||= new RenderingCancelledException(`Rendering cancelled, page ${this._pageIndex + 1}`, extraDelay);
    this.callback(error);
    this.task.onError?.(error);
  }
  operatorListChanged() {
    if (!this.graphicsReady) {
      this.graphicsReadyCallback ||= this._continueBound;
      return;
    }
    this.#dependencyTracker?.growOperationsCount(this.operatorList.fnArray.length);
    this.stepper?.updateOperatorList(this.operatorList);
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
      this.#rAF = window.requestAnimationFrame(() => {
        this.#rAF = null;
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
    if (!this.#rendererTask) {
      const gpuPromise = this.#waitForGPU?.();
      if (gpuPromise) {
        await gpuPromise;
        if (this.cancelled) {
          return;
        }
      }
    }
    const {
      operatorList
    } = this;
    const {
      lastChunk
    } = operatorList;
    if (this.#rendererTask) {
      this.operatorListIdx = await this.#rendererTask.executeOperatorList(operatorList, this.operatorListIdx, this._operationsFilter);
      if (this.cancelled) {
        return;
      }
      if (this.operatorListIdx !== operatorList.argsArray.length || lastChunk !== operatorList.lastChunk) {
        this._continue();
        return;
      }
    } else {
      this.operatorListIdx = this.gfx.executeOperatorList(operatorList, this.operatorListIdx, this._continueBound, null, this.stepper, this._operationsFilter);
    }
    if (this.operatorListIdx === operatorList.argsArray.length) {
      this.running = false;
      if (lastChunk) {
        this.gfx?.endDrawing();
        InternalRenderTask.#canvasInUse.delete(this._canvas);
        this.callback();
      }
    }
  }
}
const version = "6.5.438";
const build = "0a4153349";

;// ./src/display/editor/color_picker.js




class ColorPicker {
  #button = null;
  #buttonSwatch = null;
  #defaultColor;
  #dropdown = null;
  #dropdownWasFromKeyboard = false;
  #isMainColorPicker = false;
  #editor = null;
  #eventBus;
  #openDropdownAC = null;
  #uiManager = null;
  static #l10nColor = null;
  static get _keyboardManager() {
    return shadow(this, "_keyboardManager", new KeyboardManager([[["Escape"], ColorPicker.prototype._hideDropdownFromKeyboard], [["Space"], ColorPicker.prototype._colorSelectFromKeyboard], [["ArrowDown", "ArrowRight"], ColorPicker.prototype._moveToNext], [["ArrowUp", "ArrowLeft"], ColorPicker.prototype._moveToPrevious], [["Home"], ColorPicker.prototype._moveToBeginning], [["End"], ColorPicker.prototype._moveToEnd]]));
  }
  constructor({
    editor = null,
    uiManager = null
  }) {
    if (editor) {
      this.#isMainColorPicker = false;
      this.#editor = editor;
    } else {
      this.#isMainColorPicker = true;
    }
    this.#uiManager = editor?._uiManager || uiManager;
    this.#eventBus = this.#uiManager._eventBus;
    this.#defaultColor = editor?.color?.toUpperCase() || this.#uiManager?.highlightColors.values().next().value || "#FFFF98";
    ColorPicker.#l10nColor ||= Object.freeze({
      blue: "pdfjs-editor-colorpicker-blue",
      green: "pdfjs-editor-colorpicker-green",
      pink: "pdfjs-editor-colorpicker-pink",
      red: "pdfjs-editor-colorpicker-red",
      yellow: "pdfjs-editor-colorpicker-yellow"
    });
  }
  renderButton() {
    const button = this.#button = document.createElement("button");
    button.className = "colorPicker";
    button.tabIndex = "0";
    button.setAttribute("data-l10n-id", "pdfjs-editor-colorpicker-button");
    button.ariaHasPopup = "true";
    if (this.#editor) {
      button.ariaControls = `${this.#editor.id}_colorpicker_dropdown`;
    }
    const signal = this.#uiManager._signal;
    button.addEventListener("click", this.#openDropdown.bind(this), {
      signal
    });
    button.addEventListener("keydown", this.#keyDown.bind(this), {
      signal
    });
    const swatch = this.#buttonSwatch = document.createElement("span");
    swatch.className = "swatch";
    swatch.ariaHidden = "true";
    swatch.style.backgroundColor = this.#defaultColor;
    button.append(swatch);
    return button;
  }
  renderMainDropdown() {
    const dropdown = this.#dropdown = this.#getDropdownRoot();
    dropdown.ariaOrientation = "horizontal";
    dropdown.ariaLabelledBy = "highlightColorPickerLabel";
    return dropdown;
  }
  #getDropdownRoot() {
    const div = document.createElement("div");
    const signal = this.#uiManager._signal;
    div.addEventListener("contextmenu", noContextMenu, {
      signal
    });
    div.className = "dropdown";
    div.role = "listbox";
    div.ariaMultiSelectable = "false";
    div.ariaOrientation = "vertical";
    div.setAttribute("data-l10n-id", "pdfjs-editor-colorpicker-dropdown");
    if (this.#editor) {
      div.id = `${this.#editor.id}_colorpicker_dropdown`;
    }
    for (const [name, color] of this.#uiManager.highlightColors) {
      const button = document.createElement("button");
      button.tabIndex = "0";
      button.role = "option";
      button.setAttribute("data-color", color);
      button.title = name;
      button.setAttribute("data-l10n-id", ColorPicker.#l10nColor[name]);
      const swatch = document.createElement("span");
      button.append(swatch);
      swatch.className = "swatch";
      swatch.style.backgroundColor = color;
      button.ariaSelected = color === this.#defaultColor;
      button.addEventListener("click", this.#colorSelect.bind(this, color), {
        signal
      });
      div.append(button);
    }
    div.addEventListener("keydown", this.#keyDown.bind(this), {
      signal
    });
    return div;
  }
  #colorSelect(color, event) {
    event.stopPropagation();
    this.#eventBus.dispatch("switchannotationeditorparams", {
      source: this,
      type: AnnotationEditorParamsType.HIGHLIGHT_COLOR,
      value: color
    });
    this.update(color);
  }
  _colorSelectFromKeyboard(event) {
    if (event.target === this.#button) {
      this.#openDropdown(event);
      return;
    }
    const color = event.target.getAttribute("data-color");
    if (!color) {
      return;
    }
    this.#colorSelect(color, event);
  }
  _moveToNext(event) {
    if (!this.#isDropdownVisible) {
      this.#openDropdown(event);
      return;
    }
    if (event.target === this.#button) {
      this.#dropdown.firstElementChild?.focus();
      return;
    }
    event.target.nextSibling?.focus();
  }
  _moveToPrevious(event) {
    if (event.target === this.#dropdown?.firstElementChild || event.target === this.#button) {
      if (this.#isDropdownVisible) {
        this._hideDropdownFromKeyboard();
      }
      return;
    }
    if (!this.#isDropdownVisible) {
      this.#openDropdown(event);
    }
    event.target.previousSibling?.focus();
  }
  _moveToBeginning(event) {
    if (!this.#isDropdownVisible) {
      this.#openDropdown(event);
      return;
    }
    this.#dropdown.firstElementChild?.focus();
  }
  _moveToEnd(event) {
    if (!this.#isDropdownVisible) {
      this.#openDropdown(event);
      return;
    }
    this.#dropdown.lastElementChild?.focus();
  }
  #keyDown(event) {
    ColorPicker._keyboardManager.exec(this, event);
  }
  #openDropdown(event) {
    if (this.#isDropdownVisible) {
      this.hideDropdown();
      return;
    }
    this.#dropdownWasFromKeyboard = event.detail === 0;
    if (!this.#openDropdownAC) {
      this.#openDropdownAC = new AbortController();
      window.addEventListener("pointerdown", this.#pointerDown.bind(this), {
        signal: this.#uiManager.combinedSignal(this.#openDropdownAC)
      });
    }
    this.#button.ariaExpanded = "true";
    if (this.#dropdown) {
      this.#dropdown.classList.remove("hidden");
      return;
    }
    const root = this.#dropdown = this.#getDropdownRoot();
    this.#button.append(root);
  }
  #pointerDown(event) {
    if (this.#dropdown?.contains(event.target)) {
      return;
    }
    this.hideDropdown();
  }
  hideDropdown() {
    this.#dropdown?.classList.add("hidden");
    this.#button.ariaExpanded = "false";
    this.#openDropdownAC?.abort();
    this.#openDropdownAC = null;
  }
  get #isDropdownVisible() {
    return this.#dropdown && !this.#dropdown.classList.contains("hidden");
  }
  _hideDropdownFromKeyboard() {
    if (this.#isMainColorPicker) {
      return;
    }
    if (!this.#isDropdownVisible) {
      this.#editor?.unselect();
      return;
    }
    this.hideDropdown();
    this.#button.focus({
      preventScroll: true,
      focusVisible: this.#dropdownWasFromKeyboard
    });
  }
  update(color) {
    if (this.#buttonSwatch) {
      this.#buttonSwatch.style.backgroundColor = color;
    }
    if (!this.#dropdown) {
      return;
    }
    const i = this.#uiManager.highlightColors.values();
    for (const child of this.#dropdown.children) {
      child.ariaSelected = i.next().value === color.toUpperCase();
    }
  }
  destroy() {
    this.#button?.remove();
    this.#button = null;
    this.#buttonSwatch = null;
    this.#dropdown?.remove();
    this.#dropdown = null;
  }
}
class BasicColorPicker {
  #input = null;
  #hasAlpha = false;
  #editor = null;
  #uiManager = null;
  static #l10nColor = null;
  constructor(editor) {
    this.#editor = editor;
    this.#uiManager = editor._uiManager;
    BasicColorPicker.#l10nColor ||= Object.freeze({
      freetext: "pdfjs-editor-color-picker-free-text-input",
      ink: "pdfjs-editor-color-picker-ink-input"
    });
  }
  renderButton() {
    if (this.#input) {
      return this.#input;
    }
    const {
      editorType,
      colorType,
      colorAndOpacityType,
      opacityType,
      color,
      opacity
    } = this.#editor;
    const hasAlpha = this.#hasAlpha = FeatureTest.isAlphaColorInputSupported && opacityType !== undefined;
    const input = this.#input = document.createElement("input");
    input.type = "color";
    if (hasAlpha) {
      input.setAttribute("alpha", "");
      const alphaHex = Util.hexNums[Math.round((opacity ?? 1) * 255)];
      input.value = (color || "#000000") + alphaHex;
    } else {
      input.value = color || "#000000";
    }
    input.className = "basicColorPicker";
    input.tabIndex = 0;
    input.setAttribute("data-l10n-id", BasicColorPicker.#l10nColor[editorType]);
    input.addEventListener("input", () => {
      if (hasAlpha) {
        const rgba = getRGBA(input.value);
        if (!rgba) {
          return;
        }
        const [r, g, b, op] = rgba;
        const hex = Util.makeHexColor(r, g, b);
        if (colorAndOpacityType !== undefined) {
          this.#uiManager.updateParams(colorAndOpacityType, {
            color: hex,
            opacity: op
          });
        } else {
          this.#uiManager.updateParams(colorType, hex);
          this.#uiManager.updateParams(opacityType, op);
        }
      } else {
        this.#uiManager.updateParams(colorType, input.value);
      }
    }, {
      signal: this.#uiManager._signal
    });
    return input;
  }
  update(value) {
    if (!this.#input) {
      return;
    }
    if (this.#hasAlpha) {
      const alphaHex = Util.hexNums[Math.round(this.#editor.opacity * 255)];
      this.#input.value = value + alphaHex;
    } else {
      this.#input.value = value;
    }
  }
  updateOpacity(value) {
    if (!this.#input || !this.#hasAlpha) {
      return;
    }
    const alphaHex = Util.hexNums[Math.round(value * 255)];
    this.#input.value = this.#editor.color + alphaHex;
  }
  destroy() {
    this.#input?.remove();
    this.#input = null;
  }
  hideDropdown() {}
}

;// ./src/shared/scripting_utils.js

function makeColorComp(n) {
  return Math.floor(MathClamp(n, 0, 1) * 255).toString(16).padStart(2, "0");
}
function scaleAndClamp(x) {
  return MathClamp(x, 0, 1) * 255;
}
class ColorConverters {
  static CMYK_G([c, y, m, k]) {
    return ["G", 1 - Math.min(1, 0.3 * c + 0.59 * m + 0.11 * y + k)];
  }
  static G_CMYK([g]) {
    return ["CMYK", 0, 0, 0, 1 - g];
  }
  static G_RGB([g]) {
    return ["RGB", g, g, g];
  }
  static G_rgb([g]) {
    g = scaleAndClamp(g);
    return [g, g, g];
  }
  static G_HTML([g]) {
    const G = makeColorComp(g);
    return `#${G}${G}${G}`;
  }
  static RGB_G([r, g, b]) {
    return ["G", 0.3 * r + 0.59 * g + 0.11 * b];
  }
  static RGB_rgb(color) {
    return color.map(scaleAndClamp);
  }
  static RGB_HTML(color) {
    return `#${color.map(makeColorComp).join("")}`;
  }
  static T_HTML() {
    return "#00000000";
  }
  static T_rgb() {
    return [null];
  }
  static CMYK_RGB([c, y, m, k]) {
    return ["RGB", 1 - Math.min(1, c + k), 1 - Math.min(1, m + k), 1 - Math.min(1, y + k)];
  }
  static CMYK_rgb([c, y, m, k]) {
    return [scaleAndClamp(1 - Math.min(1, c + k)), scaleAndClamp(1 - Math.min(1, m + k)), scaleAndClamp(1 - Math.min(1, y + k))];
  }
  static CMYK_HTML(components) {
    const rgb = this.CMYK_RGB(components).slice(1);
    return this.RGB_HTML(rgb);
  }
  static RGB_CMYK([r, g, b]) {
    const c = 1 - r;
    const m = 1 - g;
    const y = 1 - b;
    const k = Math.min(c, m, y);
    return ["CMYK", c, m, y, k];
  }
}
const DateFormats = (/* unused pure expression or super */ null && (["m/d", "m/d/yy", "mm/dd/yy", "mm/yy", "d-mmm", "d-mmm-yy", "dd-mmm-yy", "yy-mm-dd", "mmm-yy", "mmmm-yy", "mmm d, yyyy", "mmmm d, yyyy", "m/d/yy h:MM tt", "m/d/yy HH:MM"]));
const TimeFormats = (/* unused pure expression or super */ null && (["HH:MM", "h:MM tt", "HH:MM:ss", "h:MM:ss tt"]));

;// ./src/display/svg_factory.js

class BaseSVGFactory {
  create(width, height, skipDimensions = false) {
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
    unreachable("Abstract method `_createSVG` called.");
  }
}
class DOMSVGFactory extends BaseSVGFactory {
  _createSVG(type) {
    return document.createElementNS(SVG_NS, type);
  }
}

;// ./src/display/annotation_layer.js





const annotation_layer_DEFAULT_FONT_SIZE = 9;
const GetElementsByNameSet = new WeakSet();
const TIMEZONE_OFFSET = new Date().getTimezoneOffset() * 60 * 1000;
class AnnotationElementFactory {
  static create(parameters) {
    const subtype = parameters.data.annotationType;
    switch (subtype) {
      case AnnotationType.LINK:
        return new LinkAnnotationElement(parameters);
      case AnnotationType.TEXT:
        return new TextAnnotationElement(parameters);
      case AnnotationType.WIDGET:
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
          case "Sig":
            return new SignatureWidgetAnnotationElement(parameters);
        }
        return new WidgetAnnotationElement(parameters);
      case AnnotationType.POPUP:
        return new PopupAnnotationElement(parameters);
      case AnnotationType.FREETEXT:
        return new FreeTextAnnotationElement(parameters);
      case AnnotationType.LINE:
        return new LineAnnotationElement(parameters);
      case AnnotationType.SQUARE:
        return new SquareAnnotationElement(parameters);
      case AnnotationType.CIRCLE:
        return new CircleAnnotationElement(parameters);
      case AnnotationType.POLYLINE:
        return new PolylineAnnotationElement(parameters);
      case AnnotationType.CARET:
        return new CaretAnnotationElement(parameters);
      case AnnotationType.INK:
        return new InkAnnotationElement(parameters);
      case AnnotationType.POLYGON:
        return new PolygonAnnotationElement(parameters);
      case AnnotationType.HIGHLIGHT:
        return new HighlightAnnotationElement(parameters);
      case AnnotationType.UNDERLINE:
        return new UnderlineAnnotationElement(parameters);
      case AnnotationType.SQUIGGLY:
        return new SquigglyAnnotationElement(parameters);
      case AnnotationType.STRIKEOUT:
        return new StrikeOutAnnotationElement(parameters);
      case AnnotationType.STAMP:
        return new StampAnnotationElement(parameters);
      case AnnotationType.FILEATTACHMENT:
        return new FileAttachmentAnnotationElement(parameters);
      case AnnotationType.RICHMEDIA:
      case AnnotationType.SCREEN:
      case AnnotationType.SOUND:
        return new MediaAnnotationElement(parameters);
      default:
        return new AnnotationElement(parameters);
    }
  }
}
class AnnotationElement {
  #updates = null;
  #hasBorder = false;
  #popupElement = null;
  constructor(parameters, {
    isRenderable = false,
    ignoreBorder = false,
    createQuadrilaterals = false
  } = {}) {
    this.isRenderable = isRenderable;
    this.data = parameters.data;
    this.layer = parameters.layer;
    this.linkService = parameters.linkService;
    this.downloadManager = parameters.downloadManager;
    this.imageResourcesPath = parameters.imageResourcesPath;
    this.renderForms = parameters.renderForms;
    this.annotationStorage = parameters.annotationStorage;
    this.enableComment = parameters.enableComment;
    this.enableAnnotationEditing = parameters.enableAnnotationEditing !== false;
    this.enableScripting = parameters.enableScripting;
    this.hasJSActions = parameters.hasJSActions;
    this._fieldObjects = parameters.fieldObjects;
    this.parent = parameters.parent;
    this.hasOwnCommentButton = false;
    if (isRenderable) {
      this.contentElement = this.container = this._createContainer(ignoreBorder);
    }
    if (createQuadrilaterals) {
      this._createQuadrilaterals();
    }
  }
  static _hasPopupData({
    contentsObj,
    richText
  }) {
    return !!(contentsObj?.str || richText?.str);
  }
  static get _svgFactory() {
    return shadow(this, "_svgFactory", new DOMSVGFactory());
  }
  get _isEditable() {
    return this.enableAnnotationEditing && this.data.isEditable;
  }
  get hasPopupData() {
    return AnnotationElement._hasPopupData(this.data) || this.enableComment && !!this.commentText;
  }
  get commentData() {
    const {
      data
    } = this;
    const editor = this.annotationStorage?.getEditor(data.id);
    return editor ? editor.getData() : data;
  }
  get hasCommentButton() {
    return this.enableComment && this.hasPopupElement;
  }
  get commentButtonPosition() {
    const editor = this.annotationStorage?.getEditor(this.data.id);
    if (editor) {
      return editor.commentButtonPositionInPage;
    }
    const {
      quadPoints,
      inkLists,
      rect
    } = this.data;
    let maxX = -Infinity;
    let maxY = -Infinity;
    if (quadPoints?.length >= 8) {
      for (let i = 0; i < quadPoints.length; i += 8) {
        if (quadPoints[i + 1] > maxY) {
          maxY = quadPoints[i + 1];
          maxX = quadPoints[i + 2];
        } else if (quadPoints[i + 1] === maxY) {
          maxX = Math.max(maxX, quadPoints[i + 2]);
        }
      }
      return [maxX, maxY];
    }
    if (inkLists?.length >= 1) {
      for (const inkList of inkLists) {
        for (let i = 0, ii = inkList.length; i < ii; i += 2) {
          if (inkList[i + 1] > maxY) {
            maxY = inkList[i + 1];
            maxX = inkList[i];
          } else if (inkList[i + 1] === maxY) {
            maxX = Math.max(maxX, inkList[i]);
          }
        }
      }
      if (maxX !== Infinity) {
        return [maxX, maxY];
      }
    }
    return rect ? [rect[2], rect[3]] : null;
  }
  _normalizePoint(point) {
    const {
      page: {
        view
      },
      viewport: {
        rawDims: {
          pageWidth,
          pageHeight,
          pageX,
          pageY
        }
      }
    } = this.parent;
    point[1] = view[3] - point[1] + view[1];
    point[0] = 100 * (point[0] - pageX) / pageWidth;
    point[1] = 100 * (point[1] - pageY) / pageHeight;
    return point;
  }
  get commentText() {
    const {
      data
    } = this;
    return this.annotationStorage.getRawValue(`${AnnotationEditorPrefix}${data.id}`)?.popup?.contents || data.contentsObj?.str || "";
  }
  set commentText(text) {
    const {
      data
    } = this;
    const popup = {
      deleted: !text,
      contents: text || ""
    };
    if (!this.annotationStorage.updateEditor(data.id, {
      popup
    })) {
      this.annotationStorage.setValue(`${AnnotationEditorPrefix}${data.id}`, {
        id: data.id,
        annotationType: data.annotationType,
        page: this.parent.page,
        popup,
        popupRef: data.popupRef,
        modificationDate: new Date()
      });
    }
    if (!text) {
      this.removePopup();
    }
  }
  removePopup() {
    (this.#popupElement?.popup || this.popup)?.remove();
    this.#popupElement = this.popup = null;
  }
  updateEdited(params) {
    if (!this.container) {
      return;
    }
    if (params.rect) {
      this.#updates ||= {
        rect: this.data.rect.slice(0)
      };
    }
    const {
      rect,
      popup: newPopup
    } = params;
    if (rect) {
      this.#setRectEdited(rect);
    }
    let popup = this.#popupElement?.popup || this.popup;
    if (!popup && newPopup?.text) {
      this._createPopup(newPopup);
      popup = this.#popupElement.popup;
    }
    if (!popup) {
      return;
    }
    popup.updateEdited(params);
    if (newPopup?.deleted) {
      popup.remove();
      this.#popupElement = null;
      this.popup = null;
    }
  }
  resetEdited() {
    if (!this.#updates) {
      return;
    }
    this.#setRectEdited(this.#updates.rect);
    this.#popupElement?.popup.resetEdited();
    this.#updates = null;
  }
  #setRectEdited(rect) {
    const {
      container: {
        style
      },
      data: {
        rect: currentRect,
        rotation
      },
      parent: {
        viewport: {
          rawDims: {
            pageWidth,
            pageHeight,
            pageX,
            pageY
          }
        }
      }
    } = this;
    currentRect?.splice(0, 4, ...rect);
    style.left = `${100 * (rect[0] - pageX) / pageWidth}%`;
    style.top = `${100 * (pageHeight - rect[3] + pageY) / pageHeight}%`;
    if (rotation === 0) {
      style.width = `${100 * (rect[2] - rect[0]) / pageWidth}%`;
      style.height = `${100 * (rect[3] - rect[1]) / pageHeight}%`;
    } else {
      this.setRotation(rotation);
    }
  }
  _createContainer(ignoreBorder) {
    const {
      data,
      parent: {
        page,
        viewport
      }
    } = this;
    const container = document.createElement("section");
    container.setAttribute("data-annotation-id", data.id);
    if (!(this instanceof WidgetAnnotationElement) && !(this instanceof LinkAnnotationElement) && !(this instanceof MediaAnnotationElement)) {
      container.tabIndex = 0;
    }
    const {
      style
    } = container;
    style.zIndex = this.parent.zIndex;
    this.parent.zIndex += 2;
    if (data.alternativeText) {
      container.title = data.alternativeText;
    }
    if (data.noRotate) {
      container.classList.add("norotate");
    }
    if (!data.rect || this instanceof PopupAnnotationElement) {
      const {
        rotation
      } = data;
      if (!data.hasOwnCanvas && rotation !== 0) {
        this.setRotation(rotation, container);
      }
      return container;
    }
    const {
      width,
      height
    } = this;
    if (!ignoreBorder && data.borderStyle.width > 0) {
      style.borderWidth = `${data.borderStyle.width}px`;
      const horizontalRadius = data.borderStyle.horizontalCornerRadius;
      const verticalRadius = data.borderStyle.verticalCornerRadius;
      if (horizontalRadius > 0 || verticalRadius > 0) {
        const radius = `calc(${horizontalRadius}px * var(--total-scale-factor)) / calc(${verticalRadius}px * var(--total-scale-factor))`;
        style.borderRadius = radius;
      }
      switch (data.borderStyle.style) {
        case AnnotationBorderStyleType.SOLID:
          style.borderStyle = "solid";
          break;
        case AnnotationBorderStyleType.DASHED:
          style.borderStyle = "dashed";
          break;
        case AnnotationBorderStyleType.BEVELED:
          warn("Unimplemented border style: beveled");
          break;
        case AnnotationBorderStyleType.INSET:
          warn("Unimplemented border style: inset");
          break;
        case AnnotationBorderStyleType.UNDERLINE:
          style.borderBottomStyle = "solid";
          break;
        default:
          break;
      }
      const borderColor = data.borderColor || null;
      if (borderColor) {
        this.#hasBorder = true;
        style.borderColor = Util.makeHexColor(...borderColor);
      } else {
        style.borderWidth = 0;
      }
    }
    const rect = Util.normalizeRect([data.rect[0], page.view[3] - data.rect[1] + page.view[1], data.rect[2], page.view[3] - data.rect[3] + page.view[1]]);
    const {
      pageWidth,
      pageHeight,
      pageX,
      pageY
    } = viewport.rawDims;
    style.left = `${100 * (rect[0] - pageX) / pageWidth}%`;
    style.top = `${100 * (rect[1] - pageY) / pageHeight}%`;
    const {
      rotation
    } = data;
    if (data.hasOwnCanvas || rotation === 0) {
      style.width = `${100 * width / pageWidth}%`;
      style.height = `${100 * height / pageHeight}%`;
    } else {
      this.setRotation(rotation, container);
    }
    return container;
  }
  setRotation(angle, container = this.container) {
    if (!this.data.rect) {
      return;
    }
    const {
      pageWidth,
      pageHeight
    } = this.parent.viewport.rawDims;
    let {
      width,
      height
    } = this;
    if (angle % 180 !== 0) {
      [width, height] = [height, width];
    }
    container.style.width = `${100 * width / pageWidth}%`;
    container.style.height = `${100 * height / pageHeight}%`;
    container.setAttribute("data-main-rotation", (360 - angle) % 360);
  }
  get _commonActions() {
    const setColor = (jsName, styleName, event) => {
      const color = event.detail[jsName];
      const colorType = color[0];
      const colorArray = color.slice(1);
      event.target.style[styleName] = ColorConverters[`${colorType}_HTML`](colorArray);
      this.annotationStorage.setValue(this.data.id, {
        [styleName]: ColorConverters[`${colorType}_rgb`](colorArray)
      });
    };
    return shadow(this, "_commonActions", {
      display: event => {
        const {
          display
        } = event.detail;
        const hidden = display % 2 === 1;
        this.container.style.visibility = hidden ? "hidden" : "visible";
        this.annotationStorage.setValue(this.data.id, {
          noView: hidden,
          noPrint: display === 1 || display === 2
        });
      },
      print: event => {
        this.annotationStorage.setValue(this.data.id, {
          noPrint: !event.detail.print
        });
      },
      hidden: event => {
        const {
          hidden
        } = event.detail;
        this.container.style.visibility = hidden ? "hidden" : "visible";
        this.annotationStorage.setValue(this.data.id, {
          noPrint: hidden,
          noView: hidden
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
        event.target.disabled = event.detail.readonly;
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
      action?.(jsEvent);
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
    if (!this.container) {
      return;
    }
    const {
      quadPoints
    } = this.data;
    if (!quadPoints) {
      return;
    }
    const [rectBlX, rectBlY, rectTrX, rectTrY] = this.data.rect.map(Math.fround);
    if (quadPoints.length === 8) {
      const [trX, trY, blX, blY] = quadPoints.subarray(2, 6);
      if (rectTrX === trX && rectTrY === trY && rectBlX === blX && rectBlY === blY) {
        return;
      }
    }
    const {
      style
    } = this.container;
    let svgBuffer;
    if (this.#hasBorder) {
      const {
        borderColor,
        borderWidth
      } = style;
      style.borderWidth = 0;
      svgBuffer = ["url('data:image/svg+xml;utf8,", `<svg xmlns="${SVG_NS}" preserveAspectRatio="none" viewBox="0 0 1 1">`, `<g fill="transparent" stroke="${borderColor}" stroke-width="${borderWidth}">`];
      this.container.classList.add("hasBorder");
    }
    const width = rectTrX - rectBlX;
    const height = rectTrY - rectBlY;
    const svgFactory = AnnotationElement._svgFactory;
    const svg = svgFactory.createElement("svg");
    svg.classList.add("quadrilateralsContainer");
    svg.setAttribute("width", 0);
    svg.setAttribute("height", 0);
    svg.role = "none";
    const defs = svgFactory.createElement("defs");
    svg.append(defs);
    const clipPath = svgFactory.createElement("clipPath");
    const id = `clippath_${this.data.id}`;
    clipPath.setAttribute("id", id);
    clipPath.setAttribute("clipPathUnits", "objectBoundingBox");
    defs.append(clipPath);
    for (let i = 2, ii = quadPoints.length; i < ii; i += 8) {
      const trX = quadPoints[i];
      const trY = quadPoints[i + 1];
      const blX = quadPoints[i + 2];
      const blY = quadPoints[i + 3];
      const rect = svgFactory.createElement("rect");
      const x = (blX - rectBlX) / width;
      const y = (rectTrY - trY) / height;
      const rectWidth = (trX - blX) / width;
      const rectHeight = (trY - blY) / height;
      rect.setAttribute("x", x);
      rect.setAttribute("y", y);
      rect.setAttribute("width", rectWidth);
      rect.setAttribute("height", rectHeight);
      clipPath.append(rect);
      svgBuffer?.push(`<rect vector-effect="non-scaling-stroke" x="${x}" y="${y}" width="${rectWidth}" height="${rectHeight}"/>`);
    }
    if (this.#hasBorder) {
      svgBuffer.push(`</g></svg>')`);
      style.backgroundImage = svgBuffer.join("");
    }
    this.container.append(svg);
    this.container.style.clipPath = `url(#${id})`;
  }
  _createPopup(popupData = null) {
    const {
      data
    } = this;
    let contentsObj, modificationDate;
    if (popupData) {
      contentsObj = {
        str: popupData.text
      };
      modificationDate = popupData.date;
    } else {
      contentsObj = data.contentsObj;
      modificationDate = data.modificationDate;
    }
    this.#popupElement = new PopupAnnotationElement({
      data: {
        color: data.color,
        titleObj: data.titleObj,
        modificationDate,
        contentsObj,
        richText: data.richText,
        parentRect: data.rect,
        borderStyle: 0,
        id: `popup_${data.id}`,
        rotation: data.rotation,
        noRotate: true
      },
      linkService: this.linkService,
      parent: this.parent,
      elements: [this]
    });
  }
  get hasPopupElement() {
    return !!(this.#popupElement || this.popup || this.data.popupRef);
  }
  get extraPopupElement() {
    return this.#popupElement;
  }
  render() {
    unreachable("Abstract method `AnnotationElement.render` called");
  }
  _getElementsByName(name, skipId = null) {
    const fields = [];
    if (this._fieldObjects) {
      const fieldObj = this._fieldObjects.get(name) || [];
      for (const {
        page,
        id,
        exportValues
      } of fieldObj) {
        if (page === -1 || id === skipId) {
          continue;
        }
        const exportValue = typeof exportValues === "string" ? exportValues : null;
        const domElement = document.querySelector(`[data-element-id="${id}"]`);
        if (domElement && !GetElementsByNameSet.has(domElement)) {
          warn(`_getElementsByName - element not allowed: ${id}`);
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
    for (const domElement of document.getElementsByName(name)) {
      const {
        exportValue
      } = domElement;
      const id = domElement.getAttribute("data-element-id");
      if (id === skipId || !GetElementsByNameSet.has(domElement)) {
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
  show() {
    if (this.container) {
      this.container.hidden = false;
    }
    this.popup?.maybeShow();
  }
  hide() {
    if (this.container) {
      this.container.hidden = true;
    }
    this.popup?.forceHide();
  }
  getElementsToTriggerPopup() {
    return this.container;
  }
  addHighlightArea() {
    const triggers = this.getElementsToTriggerPopup();
    if (Array.isArray(triggers)) {
      for (const element of triggers) {
        element.classList.add("highlightArea");
      }
    } else {
      triggers.classList.add("highlightArea");
    }
  }
  _editOnDoubleClick() {
    if (!this._isEditable) {
      return;
    }
    const {
      annotationEditorType: mode,
      data: {
        id: editId
      }
    } = this;
    this.container.addEventListener("dblclick", () => {
      this.linkService.eventBus?.dispatch("switchannotationeditormode", {
        source: this,
        mode,
        editId,
        mustEnterInEditMode: true
      });
    });
  }
  updateOC(optionalContentConfig) {
    if (!this.data.oc || !optionalContentConfig) {
      return;
    }
    const isVisible = optionalContentConfig.isVisible(this.data.oc);
    if (isVisible) {
      this.show();
    } else {
      this.hide();
    }
  }
  get width() {
    return this.data.rect[2] - this.data.rect[0];
  }
  get height() {
    return this.data.rect[3] - this.data.rect[1];
  }
  _setBackgroundColor(element) {
    const color = this.data.backgroundColor || null;
    element.style.backgroundColor = color === null ? "transparent" : Util.makeHexColor(...color);
  }
}
class EditorAnnotationElement extends AnnotationElement {
  constructor(parameters) {
    super(parameters, {
      isRenderable: true,
      ignoreBorder: true
    });
    this.editor = parameters.editor;
  }
  render() {
    this.container.className = "editorAnnotation";
    return this.container;
  }
  createOrUpdatePopup() {
    const {
      editor
    } = this;
    if (!editor.hasComment) {
      return;
    }
    this._createPopup(editor.comment);
  }
  get hasCommentButton() {
    return this.enableComment && this.editor.hasComment;
  }
  get commentButtonPosition() {
    return this.editor.commentButtonPositionInPage;
  }
  get commentText() {
    return this.editor.comment.text;
  }
  set commentText(text) {
    this.editor.comment = text;
    if (!text) {
      this.removePopup();
    }
  }
  get commentData() {
    return this.editor.getData();
  }
  remove() {
    this.parent.removeAnnotation(this.data.id);
    this.container.remove();
    this.container = null;
    this.removePopup();
  }
}
class LinkAnnotationElement extends AnnotationElement {
  constructor(parameters, options = null) {
    super(parameters, {
      isRenderable: true,
      ignoreBorder: !!options?.ignoreBorder,
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
      this._bindNamedAction(link, data.action, data.overlaidText);
      isBound = true;
    } else if (data.attachment) {
      this.#bindAttachment(link, data.attachmentId, data.attachment, data.overlaidText, data.attachmentDest);
      isBound = true;
    } else if (data.setOCGState) {
      this.#bindSetOCGState(link, data.setOCGState, data.overlaidText);
      isBound = true;
    } else if (data.dest) {
      this._bindLink(link, data.dest, data.overlaidText);
      isBound = true;
    } else {
      if (data.actions && (data.actions.has("Action") || data.actions.has("Mouse Up") || data.actions.has("Mouse Down")) && this.enableScripting && this.hasJSActions) {
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
    this.container.classList.add("linkAnnotation");
    if (isBound) {
      this.contentElement = link;
      this.container.append(link);
    }
    return this.container;
  }
  #setInternalLink() {
    this.container.setAttribute("data-internal-link", "");
  }
  _bindLink(link, destination, overlaidText = "") {
    link.href = this.linkService.getDestinationHash(destination);
    link.onclick = () => {
      if (destination) {
        this.linkService.goToDestination(destination);
      }
      return false;
    };
    if (destination || destination === "") {
      this.#setInternalLink();
    }
    if (overlaidText) {
      link.title = overlaidText;
    }
  }
  _bindNamedAction(link, action, overlaidText = "") {
    link.href = this.linkService.getAnchorUrl("");
    link.onclick = () => {
      this.linkService.executeNamedAction(action);
      return false;
    };
    if (overlaidText) {
      link.title = overlaidText;
    }
    this.#setInternalLink();
  }
  #bindAttachment(link, attachmentId, attachment, overlaidText = "", dest = null) {
    link.href = this.linkService.getAnchorUrl("");
    if (attachment.description) {
      link.title = attachment.description;
    } else if (overlaidText) {
      link.title = overlaidText;
    }
    const openAttachment = async () => {
      const content = await this.linkService.getAttachmentContent(attachmentId);
      if (content) {
        this.downloadManager?.openOrDownloadData(content, attachment.filename, dest);
      }
    };
    link.onclick = () => {
      openAttachment();
      return false;
    };
    this.#setInternalLink();
  }
  #bindSetOCGState(link, action, overlaidText = "") {
    link.href = this.linkService.getAnchorUrl("");
    link.onclick = () => {
      this.linkService.executeSetOCGState(action);
      return false;
    };
    if (overlaidText) {
      link.title = overlaidText;
    }
    this.#setInternalLink();
  }
  _bindJSAction(link, {
    actions,
    id,
    overlaidText
  }) {
    link.href = this.linkService.getAnchorUrl("");
    const map = new Map([["Action", "onclick"], ["Mouse Up", "onmouseup"], ["Mouse Down", "onmousedown"]]);
    for (const name of actions.keys()) {
      const jsName = map.get(name);
      if (!jsName) {
        continue;
      }
      link[jsName] = () => {
        this.linkService.eventBus?.dispatch("dispatcheventinsandbox", {
          source: this,
          detail: {
            id,
            name
          }
        });
        return false;
      };
    }
    if (overlaidText) {
      link.title = overlaidText;
    }
    link.onclick ||= () => false;
    this.#setInternalLink();
  }
  _bindResetFormAction(link, resetForm) {
    const otherClickAction = link.onclick;
    if (!otherClickAction) {
      link.href = this.linkService.getAnchorUrl("");
    }
    this.#setInternalLink();
    if (!this._fieldObjects) {
      warn(`_bindResetFormAction - "resetForm" action not supported, ` + "ensure that the `fieldObjects` parameter is provided.");
      if (!otherClickAction) {
        link.onclick = () => false;
      }
      return;
    }
    link.onclick = () => {
      otherClickAction?.();
      const {
        fields: resetFormFields,
        refs: resetFormRefs,
        include
      } = resetForm;
      const allFields = [];
      if (resetFormFields.length !== 0 || resetFormRefs.length !== 0) {
        const fieldIds = new Set(resetFormRefs);
        for (const fieldName of resetFormFields) {
          const fields = this._fieldObjects.get(fieldName) || [];
          for (const {
            id
          } of fields) {
            fieldIds.add(id);
          }
        }
        const kidIdsById = new Map();
        for (const fields of this._fieldObjects.values()) {
          for (const {
            id,
            kidIds
          } of fields) {
            if (kidIds) {
              kidIdsById.set(id, kidIds);
            }
          }
        }
        for (const id of fieldIds) {
          for (const kidId of kidIdsById.get(id) || []) {
            fieldIds.add(kidId);
          }
        }
        for (const fields of this._fieldObjects.values()) {
          for (const field of fields) {
            if (fieldIds.has(field.id) === include) {
              allFields.push(field);
            }
          }
        }
      } else {
        for (const fields of this._fieldObjects.values()) {
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
          warn(`_bindResetFormAction - element not allowed: ${id}`);
          continue;
        }
        domElement.dispatchEvent(new Event("resetform"));
      }
      if (this.enableScripting) {
        this.linkService.eventBus?.dispatch("dispatcheventinsandbox", {
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
    super(parameters, {
      isRenderable: true
    });
  }
  render() {
    this.container.classList.add("textAnnotation");
    const image = document.createElement("img");
    image.src = this.imageResourcesPath + "annotation-" + this.data.name.toLowerCase() + ".svg";
    image.setAttribute("data-l10n-id", "pdfjs-text-annotation-type");
    image.setAttribute("data-l10n-args", JSON.stringify({
      type: this.data.name
    }));
    if (!this.data.popupRef && this.hasPopupData) {
      this.hasOwnCommentButton = true;
      this._createPopup();
    }
    this.container.append(image);
    return this.container;
  }
}
class WidgetAnnotationElement extends AnnotationElement {
  render() {
    return this.container;
  }
  _getKeyModifier(event) {
    return FeatureTest.platform.isMac ? event.metaKey : event.ctrlKey;
  }
  _setEventListener(element, elementData, baseName, eventName, valueGetter) {
    if (baseName.includes("mouse")) {
      element.addEventListener(baseName, event => {
        this.linkService.eventBus?.dispatch("dispatcheventinsandbox", {
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
        if (baseName === "blur") {
          if (!elementData.focused || !event.relatedTarget) {
            return;
          }
          elementData.focused = false;
        } else if (baseName === "focus") {
          if (elementData.focused) {
            return;
          }
          elementData.focused = true;
        }
        if (!valueGetter) {
          return;
        }
        this.linkService.eventBus?.dispatch("dispatcheventinsandbox", {
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
  _setEventListeners(element, elementData, names, getter) {
    const {
      actions
    } = this.data;
    for (const [baseName, eventName] of names) {
      if (eventName === "Action" || actions?.has(eventName)) {
        if (eventName === "Focus" || eventName === "Blur") {
          elementData ||= {
            focused: false
          };
        }
        this._setEventListener(element, elementData, baseName, eventName, getter);
        if (eventName === "Focus" && !actions?.has("Blur")) {
          this._setEventListener(element, elementData, "blur", "Blur", null);
        } else if (eventName === "Blur" && !actions?.has("Focus")) {
          this._setEventListener(element, elementData, "focus", "Focus", null);
        }
      }
    }
  }
  _setTextStyle(element) {
    const TEXT_ALIGNMENT = ["left", "center", "right"];
    const {
      fontColor
    } = this.data.defaultAppearanceData;
    const fontSize = this.data.defaultAppearanceData.fontSize || annotation_layer_DEFAULT_FONT_SIZE;
    const style = element.style;
    let computedFontSize;
    const BORDER_SIZE = 2;
    const roundToOneDecimal = x => Math.round(10 * x) / 10;
    if (this.data.multiLine) {
      const height = Math.abs(this.data.rect[3] - this.data.rect[1] - BORDER_SIZE);
      const numberOfLines = Math.round(height / ((/* inlined export .LINE_FACTOR */1.35) * fontSize)) || 1;
      const lineHeight = height / numberOfLines;
      computedFontSize = Math.min(fontSize, roundToOneDecimal(lineHeight / (/* inlined export .LINE_FACTOR */1.35)));
    } else {
      const height = Math.abs(this.data.rect[3] - this.data.rect[1] - BORDER_SIZE);
      computedFontSize = Math.min(fontSize, roundToOneDecimal(height / (/* inlined export .LINE_FACTOR */1.35)));
    }
    style.fontSize = `calc(${computedFontSize}px * var(--total-scale-factor))`;
    style.color = Util.makeHexColor(...fontColor);
    if (this.data.textAlignment !== null && !this.data.comb) {
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
    const isRenderable = parameters.renderForms || parameters.data.hasOwnCanvas || !parameters.data.hasAppearance && !!parameters.data.fieldValue;
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
    this.container.classList.add("textWidgetAnnotation");
    let element = null;
    if (this.renderForms) {
      const storedData = storage.getValue(id, {
        value: this.data.fieldValue
      });
      let textContent = storedData.value || "";
      const maxLen = storage.getValue(id, {
        charLimit: this.data.maxLen
      }).charLimit;
      if (maxLen && textContent.length > maxLen) {
        textContent = textContent.slice(0, maxLen);
      }
      let fieldFormattedValues = storedData.formattedValue || this.data.textContent?.join("\n") || null;
      if (fieldFormattedValues && this.data.comb) {
        fieldFormattedValues = fieldFormattedValues.replaceAll(/\s+/g, "");
      }
      const elementData = {
        userValue: textContent,
        formattedValue: fieldFormattedValues,
        lastCommittedValue: null,
        commitKey: 1,
        focused: false
      };
      if (this.data.multiLine) {
        element = document.createElement("textarea");
        element.textContent = fieldFormattedValues ?? textContent;
        if (this.data.doNotScroll) {
          element.style.overflowY = "hidden";
        }
      } else {
        element = document.createElement("input");
        element.type = this.data.password ? "password" : "text";
        element.setAttribute("value", fieldFormattedValues ?? textContent);
        if (this.data.doNotScroll) {
          element.style.overflowX = "hidden";
        }
      }
      if (this.data.hasOwnCanvas) {
        this.container.classList.add("hasOwnCanvas");
        if (storage.has(id)) {
          this.container.classList.add("sandboxModified");
        }
      }
      GetElementsByNameSet.add(element);
      this.contentElement = element;
      element.setAttribute("data-element-id", id);
      element.disabled = this.data.readOnly;
      element.name = this.data.fieldName;
      element.tabIndex = 0;
      const {
        datetimeFormat,
        datetimeType,
        timeStep
      } = this.data;
      const hasDateOrTime = !!datetimeType && this.enableScripting;
      if (datetimeFormat) {
        element.title = datetimeFormat;
      }
      this._setRequired(element, this.data.required);
      if (maxLen) {
        element.maxLength = maxLen;
      }
      element.addEventListener("input", event => {
        storage.setValue(id, {
          value: event.target.value
        });
        this.setPropertyOnSiblings(element, "value", event.target.value, "value");
        elementData.formattedValue = null;
      });
      element.addEventListener("resetform", event => {
        const defaultValue = this.data.defaultFieldValue ?? "";
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
        element.addEventListener("focus", event => {
          if (elementData.focused) {
            return;
          }
          const {
            target
          } = event;
          if (hasDateOrTime) {
            target.type = datetimeType;
            if (timeStep) {
              target.step = timeStep;
            }
          }
          if (elementData.userValue) {
            const value = elementData.userValue;
            if (hasDateOrTime) {
              if (datetimeType === "time") {
                const date = new Date(value);
                const parts = [date.getHours(), date.getMinutes(), date.getSeconds()];
                target.value = parts.map(v => v.toString().padStart(2, "0")).join(":");
              } else {
                target.value = new Date(value - TIMEZONE_OFFSET).toISOString().split(datetimeType === "date" ? "T" : ".", 1)[0];
              }
            } else {
              target.value = value;
            }
          }
          elementData.lastCommittedValue = target.value;
          elementData.commitKey = 1;
          if (!this.data.actions?.has("Focus")) {
            elementData.focused = true;
          }
        });
        element.addEventListener("updatefromsandbox", jsEvent => {
          this.container.classList.add("sandboxModified");
          const actions = {
            value(event) {
              elementData.userValue = event.detail.value ?? "";
              if (!hasDateOrTime) {
                storage.setValue(id, {
                  value: elementData.userValue.toString()
                });
              }
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
              const data = {
                formattedValue
              };
              if (hasDateOrTime) {
                data.value = formattedValue;
              }
              storage.setValue(id, data);
            },
            selRange(event) {
              event.target.setSelectionRange(...event.detail.selRange);
            },
            charLimit: event => {
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
              this.linkService.eventBus?.dispatch("dispatcheventinsandbox", {
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
          elementData.commitKey = 1;
          let commitKey = -1;
          if (event.key === "Escape") {
            commitKey = 0;
          } else if (event.key === "Enter" && !this.data.multiLine) {
            commitKey = 2;
          } else if (event.key === "Tab") {
            elementData.commitKey = 3;
          }
          if (commitKey === -1) {
            return;
          }
          const {
            value
          } = event.target;
          if (elementData.lastCommittedValue === value) {
            return;
          }
          elementData.lastCommittedValue = value;
          elementData.userValue = value;
          this.linkService.eventBus?.dispatch("dispatcheventinsandbox", {
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
          if (!elementData.focused || !event.relatedTarget) {
            return;
          }
          if (!this.data.actions?.has("Blur")) {
            elementData.focused = false;
          }
          const {
            target
          } = event;
          let {
            value
          } = target;
          if (hasDateOrTime) {
            if (value && datetimeType === "time") {
              const parts = value.split(":").map(v => parseInt(v, 10));
              value = new Date(2000, 0, 1, parts[0], parts[1], parts[2] || 0).valueOf();
              target.step = "";
            } else {
              if (!value.includes("T")) {
                value = `${value}T00:00`;
              }
              value = new Date(value).valueOf();
            }
            target.type = "text";
          }
          elementData.userValue = value;
          if (elementData.lastCommittedValue !== value) {
            this.linkService.eventBus?.dispatch("dispatcheventinsandbox", {
              source: this,
              detail: {
                id,
                name: "Keystroke",
                value,
                willCommit: true,
                commitKey: elementData.commitKey,
                selStart: event.target.selectionStart,
                selEnd: event.target.selectionEnd
              }
            });
          }
          _blurListener(event);
        });
        if (this.data.actions?.has("Keystroke")) {
          element.addEventListener("beforeinput", event => {
            elementData.lastCommittedValue = null;
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
                  const wordCharPattern = /\w/;
                  while (selStart > 0 && !wordCharPattern.test(value[selStart - 1])) {
                    selStart--;
                  }
                  while (selStart > 0 && wordCharPattern.test(value[selStart - 1])) {
                    selStart--;
                  }
                  break;
                }
              case "deleteWordForward":
                {
                  const match = value.substring(selectionStart).match(/^\W*\w*/);
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
            this.linkService.eventBus?.dispatch("dispatcheventinsandbox", {
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
        this._setEventListeners(element, elementData, [["focus", "Focus"], ["blur", "Blur"], ["mousedown", "Mouse Down"], ["mouseenter", "Mouse Enter"], ["mouseleave", "Mouse Exit"], ["mouseup", "Mouse Up"]], event => event.target.value);
      }
      if (blurListener) {
        element.addEventListener("blur", blurListener);
      }
      if (this.data.comb) {
        const fieldWidth = this.data.rect[2] - this.data.rect[0];
        const combWidth = fieldWidth / maxLen;
        element.classList.add("comb");
        element.style.setProperty("--comb-width", `calc(${combWidth}px * var(--total-scale-factor))`);
        const alignment = this.data.textAlignment;
        if (alignment === 1 || alignment === 2) {
          const setCombOffset = () => {
            const free = maxLen - element.value.length;
            element.style.setProperty("--comb-offset", `${alignment === 1 ? free >> 1 : free}`);
          };
          setCombOffset();
          for (const evt of ["input", "blur", "resetform", "updatefromsandbox"]) {
            element.addEventListener(evt, setCombOffset);
          }
        }
      }
    } else {
      element = document.createElement("div");
      element.textContent = this.data.fieldValue;
      element.style.verticalAlign = "middle";
      element.style.display = "table-cell";
      if (this.data.hasOwnCanvas) {
        element.hidden = true;
      }
    }
    this._setTextStyle(element);
    this._setBackgroundColor(element);
    this._setDefaultPropertiesFromJS(element);
    this.container.append(element);
    return this.container;
  }
}
class SignatureWidgetAnnotationElement extends WidgetAnnotationElement {
  constructor(parameters) {
    super(parameters, {
      isRenderable: !!parameters.data.hasOwnCanvas
    });
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
    this.container.classList.add("buttonWidgetAnnotation", "checkBox");
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
    element.tabIndex = 0;
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
      this._setEventListeners(element, null, [["change", "Validate"], ["change", "Action"], ["focus", "Focus"], ["blur", "Blur"], ["mousedown", "Mouse Down"], ["mouseenter", "Mouse Enter"], ["mouseleave", "Mouse Exit"], ["mouseup", "Mouse Up"]], event => event.target.checked);
    }
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
    this.container.classList.add("buttonWidgetAnnotation", "radioButton");
    const storage = this.annotationStorage;
    const data = this.data;
    const id = data.id;
    let value = storage.getValue(id, {
      value: data.buttonValue !== null && data.fieldValue === data.buttonValue
    }).value;
    if (typeof value === "string") {
      value = value !== data.buttonValue;
      storage.setValue(id, {
        value
      });
    }
    if (value) {
      for (const radio of this._getElementsByName(data.fieldName, id)) {
        storage.setValue(radio.id, {
          value: false
        });
      }
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
    element.tabIndex = 0;
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
      this._setEventListeners(element, null, [["change", "Validate"], ["change", "Action"], ["focus", "Focus"], ["blur", "Blur"], ["mousedown", "Mouse Down"], ["mouseenter", "Mouse Enter"], ["mouseleave", "Mouse Exit"], ["mouseup", "Mouse Up"]], event => event.target.checked);
    }
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
    container.classList.add("buttonWidgetAnnotation", "pushButton");
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
    this.container.classList.add("choiceWidgetAnnotation");
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
    selectElement.tabIndex = 0;
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
    const fixDisplayValue = (option, value) => {
      const newValue = value.replaceAll(" ", "\u00A0");
      option.textContent = newValue;
      if (newValue !== value) {
        option.setAttribute("display-value", value);
      }
    };
    for (const option of this.data.options) {
      const optionElement = document.createElement("option");
      fixDisplayValue(optionElement, option.displayValue);
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
    const getValue = isExport => {
      const name = isExport ? "value" : "textContent";
      const {
        options,
        multiple
      } = selectElement;
      if (!multiple) {
        return options.selectedIndex === -1 ? null : options[options.selectedIndex][name];
      }
      return Array.prototype.filter.call(options, option => option.selected).map(option => option[name]);
    };
    let selectedValues = getValue(false);
    const getItems = event => {
      const options = event.target.options;
      return Array.prototype.map.call(options, option => ({
        displayValue: option.getAttribute("display-value") || option.textContent,
        exportValue: option.value
      }));
    };
    if (this.enableScripting && this.hasJSActions) {
      selectElement.addEventListener("updatefromsandbox", jsEvent => {
        const actions = {
          value(event) {
            removeEmptyEntry?.();
            const value = event.detail.value;
            const values = new Set(Array.isArray(value) ? value : [value]);
            for (const option of selectElement.options) {
              option.selected = values.has(option.value);
            }
            storage.setValue(id, {
              value: getValue(true)
            });
            selectedValues = getValue(false);
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
              value: getValue(true),
              items: getItems(event)
            });
            selectedValues = getValue(false);
          },
          clear(event) {
            while (selectElement.length !== 0) {
              selectElement.remove(0);
            }
            storage.setValue(id, {
              value: null,
              items: []
            });
            selectedValues = getValue(false);
          },
          insert(event) {
            const {
              index,
              displayValue,
              exportValue
            } = event.detail.insert;
            const selectChild = selectElement.children[index];
            const optionElement = document.createElement("option");
            fixDisplayValue(optionElement, displayValue);
            optionElement.value = exportValue;
            if (selectChild) {
              selectChild.before(optionElement);
            } else {
              selectElement.append(optionElement);
            }
            storage.setValue(id, {
              value: getValue(true),
              items: getItems(event)
            });
            selectedValues = getValue(false);
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
              fixDisplayValue(optionElement, displayValue);
              optionElement.value = exportValue;
              selectElement.append(optionElement);
            }
            if (selectElement.options.length > 0) {
              selectElement.options[0].selected = true;
            }
            storage.setValue(id, {
              value: getValue(true),
              items: getItems(event)
            });
            selectedValues = getValue(false);
          },
          indices(event) {
            const indices = new Set(event.detail.indices);
            for (const option of event.target.options) {
              option.selected = indices.has(option.index);
            }
            storage.setValue(id, {
              value: getValue(true)
            });
            selectedValues = getValue(false);
          },
          editable(event) {
            event.target.disabled = !event.detail.editable;
          }
        };
        this._dispatchEventFromSandbox(actions, jsEvent);
      });
      selectElement.addEventListener("input", event => {
        const exportValue = getValue(true);
        const change = getValue(false);
        storage.setValue(id, {
          value: exportValue
        });
        event.preventDefault();
        this.linkService.eventBus?.dispatch("dispatcheventinsandbox", {
          source: this,
          detail: {
            id,
            name: "Keystroke",
            value: selectedValues,
            change,
            changeEx: exportValue,
            willCommit: false,
            commitKey: 1,
            keyDown: false
          }
        });
      });
      this._setEventListeners(selectElement, null, [["focus", "Focus"], ["blur", "Blur"], ["mousedown", "Mouse Down"], ["mouseenter", "Mouse Enter"], ["mouseleave", "Mouse Exit"], ["mouseup", "Mouse Up"], ["input", "Action"], ["input", "Validate"]], event => event.target.value);
    } else {
      selectElement.addEventListener("input", function (event) {
        storage.setValue(id, {
          value: getValue(true)
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
    const {
      data,
      elements,
      parent
    } = parameters;
    const hasCommentManager = !!parent._commentManager;
    super(parameters, {
      isRenderable: !hasCommentManager && AnnotationElement._hasPopupData(data)
    });
    this.elements = elements;
    if (hasCommentManager && AnnotationElement._hasPopupData(data)) {
      const popup = this.popup = this.#createPopup();
      for (const element of elements) {
        element.popup = popup;
      }
    } else {
      this.popup = null;
    }
  }
  #createPopup() {
    return new PopupElement({
      container: this.container,
      color: this.data.color,
      titleObj: this.data.titleObj,
      modificationDate: this.data.modificationDate || this.data.creationDate,
      contentsObj: this.data.contentsObj,
      richText: this.data.richText,
      rect: this.data.rect,
      parentRect: this.data.parentRect || null,
      parent: this.parent,
      elements: this.elements,
      open: this.data.open,
      commentManager: this.parent._commentManager
    });
  }
  render() {
    const {
      container
    } = this;
    container.classList.add("popupAnnotation");
    container.role = "comment";
    const popup = this.popup = this.#createPopup();
    const elementIds = [];
    for (const element of this.elements) {
      element.popup = popup;
      element.container.ariaHasPopup = "dialog";
      elementIds.push(element.data.id);
      element.addHighlightArea();
    }
    this.container.setAttribute("aria-controls", elementIds.map(id => `${AnnotationPrefix}${id}`).join(","));
    return this.container;
  }
}
class PopupElement {
  #commentManager = null;
  #boundKeyDown = this.#keyDown.bind(this);
  #boundHide = this.#hide.bind(this);
  #boundShow = this.#show.bind(this);
  #boundToggle = this.#toggle.bind(this);
  #color = null;
  #container = null;
  #contentsObj = null;
  #dateObj = null;
  #elements = null;
  #parent = null;
  #parentRect = null;
  #pinned = false;
  #popup = null;
  #popupAbortController = null;
  #position = null;
  #commentButton = null;
  #commentButtonPosition = null;
  #popupPosition = null;
  #rect = null;
  #richText = null;
  #titleObj = null;
  #updates = null;
  #wasVisible = false;
  #firstElement = null;
  #commentText = null;
  constructor({
    container,
    color,
    elements,
    titleObj,
    modificationDate,
    contentsObj,
    richText,
    parent,
    rect,
    parentRect,
    open,
    commentManager = null
  }) {
    this.#container = container;
    this.#titleObj = titleObj;
    this.#contentsObj = contentsObj;
    this.#richText = richText;
    this.#parent = parent;
    this.#color = color;
    this.#rect = rect;
    this.#parentRect = parentRect;
    this.#elements = elements;
    this.#commentManager = commentManager;
    this.#firstElement = elements[0];
    this.#dateObj = PDFDateString.toDateObject(modificationDate);
    this.trigger = elements.flatMap(e => e.getElementsToTriggerPopup());
    if (!commentManager) {
      this.#addEventListeners();
      this.#container.hidden = true;
      if (open) {
        this.#toggle();
      }
    }
  }
  #addEventListeners() {
    if (this.#popupAbortController) {
      return;
    }
    this.#popupAbortController = new AbortController();
    const {
      signal
    } = this.#popupAbortController;
    for (const element of this.trigger) {
      element.addEventListener("click", this.#boundToggle, {
        signal
      });
      element.addEventListener("pointerenter", this.#boundShow, {
        signal
      });
      element.addEventListener("pointerleave", this.#boundHide, {
        signal
      });
      element.classList.add("popupTriggerArea");
    }
    for (const element of this.#elements) {
      element.container?.addEventListener("keydown", this.#boundKeyDown, {
        signal
      });
    }
  }
  #setCommentButtonPosition() {
    const element = this.#elements.find(e => e.hasCommentButton);
    if (!element) {
      return;
    }
    this.#commentButtonPosition = element._normalizePoint(element.commentButtonPosition);
  }
  renderCommentButton() {
    if (this.#commentButton) {
      if (!this.#commentButton.parentNode) {
        this.#firstElement.container.after(this.#commentButton);
      }
      return;
    }
    if (!this.#commentButtonPosition) {
      this.#setCommentButtonPosition();
    }
    if (!this.#commentButtonPosition) {
      return;
    }
    const {
      signal
    } = this.#popupAbortController = new AbortController();
    const hasOwnButton = this.#firstElement.hasOwnCommentButton;
    const togglePopup = () => {
      this.#commentManager.toggleCommentPopup(this, true, undefined, !hasOwnButton);
    };
    const showPopup = () => {
      this.#commentManager.toggleCommentPopup(this, false, true, !hasOwnButton);
    };
    const hidePopup = () => {
      this.#commentManager.toggleCommentPopup(this, false, false);
    };
    if (!hasOwnButton) {
      const button = this.#commentButton = document.createElement("button");
      button.className = "annotationCommentButton";
      const parentContainer = this.#firstElement.container;
      button.style.zIndex = parseInt(parentContainer.style.zIndex, 10) + 1;
      button.tabIndex = 0;
      button.ariaHasPopup = "dialog";
      button.ariaControls = "commentPopup";
      button.setAttribute("data-l10n-id", "pdfjs-show-comment-button");
      this.#updateColor();
      this.#updateCommentButtonPosition();
      button.addEventListener("keydown", this.#boundKeyDown, {
        signal
      });
      button.addEventListener("click", togglePopup, {
        signal
      });
      button.addEventListener("pointerenter", showPopup, {
        signal
      });
      button.addEventListener("pointerleave", hidePopup, {
        signal
      });
      parentContainer.after(button);
    } else {
      this.#commentButton = this.#firstElement.container;
      for (const element of this.trigger) {
        element.ariaHasPopup = "dialog";
        element.ariaControls = "commentPopup";
        element.addEventListener("keydown", this.#boundKeyDown, {
          signal
        });
        element.addEventListener("click", togglePopup, {
          signal
        });
        element.addEventListener("pointerenter", showPopup, {
          signal
        });
        element.addEventListener("pointerleave", hidePopup, {
          signal
        });
        element.classList.add("popupTriggerArea");
      }
    }
  }
  #updateCommentButtonPosition() {
    if (this.#firstElement.extraPopupElement && !this.#firstElement.editor) {
      return;
    }
    if (!this.#commentButton) {
      this.renderCommentButton();
    }
    const [x, y] = this.#commentButtonPosition;
    const {
      style
    } = this.#commentButton;
    style.left = `calc(${x}%)`;
    style.top = `calc(${y}% - var(--comment-button-dim))`;
  }
  #updateColor() {
    if (this.#firstElement.extraPopupElement) {
      return;
    }
    if (!this.#commentButton) {
      this.renderCommentButton();
    }
    this.#commentButton.style.backgroundColor = this.commentButtonColor || "";
  }
  get commentButtonColor() {
    const {
      color,
      opacity
    } = this.#firstElement.commentData;
    return !color ? null : this.#parent._commentManager.makeCommentColor(color, opacity);
  }
  focusCommentButton() {
    setTimeout(() => {
      this.#commentButton?.focus();
    }, 0);
  }
  getData() {
    const {
      richText,
      color,
      opacity,
      creationDate,
      modificationDate
    } = this.#firstElement.commentData;
    return {
      contentsObj: {
        str: this.comment
      },
      richText,
      color,
      opacity,
      creationDate,
      modificationDate
    };
  }
  get elementBeforePopup() {
    return this.#commentButton;
  }
  get comment() {
    this.#commentText ||= this.#firstElement.commentText;
    return this.#commentText;
  }
  set comment(text) {
    if (text === this.comment) {
      return;
    }
    this.#firstElement.commentText = this.#commentText = text;
  }
  focus() {
    this.#firstElement.container?.focus();
  }
  get parentBoundingClientRect() {
    return this.#firstElement.layer.getBoundingClientRect();
  }
  setCommentButtonStates({
    selected,
    hasPopup
  }) {
    if (!this.#commentButton) {
      return;
    }
    this.#commentButton.classList.toggle("selected", selected);
    this.#commentButton.ariaExpanded = hasPopup;
  }
  setSelectedCommentButton(selected) {
    this.#commentButton.classList.toggle("selected", selected);
  }
  get commentPopupPosition() {
    if (this.#popupPosition) {
      return this.#popupPosition;
    }
    const {
      x,
      y,
      height
    } = this.#commentButton.getBoundingClientRect();
    const {
      x: parentX,
      y: parentY,
      width: parentWidth,
      height: parentHeight
    } = this.#firstElement.layer.getBoundingClientRect();
    return [(x - parentX) / parentWidth, (y + height - parentY) / parentHeight];
  }
  set commentPopupPosition(pos) {
    this.#popupPosition = pos;
  }
  hasDefaultPopupPosition() {
    return this.#popupPosition === null;
  }
  get commentButtonPosition() {
    return this.#commentButtonPosition;
  }
  get commentButtonWidth() {
    return this.#commentButton.getBoundingClientRect().width / this.parentBoundingClientRect.width;
  }
  editComment(options) {
    const [posX, posY] = this.#popupPosition || this.commentButtonPosition.map(x => x / 100);
    const parentDimensions = this.parentBoundingClientRect;
    const {
      x: parentX,
      y: parentY,
      width: parentWidth,
      height: parentHeight
    } = parentDimensions;
    this.#commentManager.showDialog(null, this, parentX + posX * parentWidth, parentY + posY * parentHeight, {
      ...options,
      parentDimensions
    });
  }
  render() {
    if (this.#popup) {
      return;
    }
    const popup = this.#popup = document.createElement("div");
    popup.className = "popup";
    if (this.#color) {
      const baseColor = popup.style.outlineColor = Util.makeHexColor(...this.#color);
      popup.style.backgroundColor = `color-mix(in srgb, ${baseColor} 30%, white)`;
    }
    const header = document.createElement("span");
    header.className = "header";
    if (this.#titleObj?.str) {
      const title = document.createElement("span");
      title.className = "title";
      header.append(title);
      ({
        dir: title.dir,
        str: title.textContent
      } = this.#titleObj);
    }
    popup.append(header);
    if (this.#dateObj) {
      const modificationDate = document.createElement("time");
      modificationDate.className = "popupDate";
      modificationDate.setAttribute("data-l10n-id", "pdfjs-annotation-date-time-string");
      modificationDate.setAttribute("data-l10n-args", JSON.stringify({
        dateObj: this.#dateObj.valueOf()
      }));
      modificationDate.dateTime = this.#dateObj.toISOString();
      header.append(modificationDate);
    }
    renderRichText({
      html: this.#html || this.#contentsObj.str,
      dir: this.#contentsObj?.dir,
      className: "popupContent"
    }, popup);
    this.#container.append(popup);
  }
  get #html() {
    const richText = this.#richText;
    const contentsObj = this.#contentsObj;
    if (richText?.str && (!contentsObj?.str || contentsObj.str === richText.str)) {
      return this.#richText.html || null;
    }
    return null;
  }
  get #fontSize() {
    return this.#html?.attributes?.style?.fontSize || 0;
  }
  get #fontColor() {
    return this.#html?.attributes?.style?.color || null;
  }
  #makePopupContent(text) {
    const popupLines = [];
    const popupContent = {
      str: text,
      html: {
        name: "div",
        attributes: {
          dir: "auto"
        },
        children: [{
          name: "p",
          children: popupLines
        }]
      }
    };
    const lineAttributes = {
      style: {
        color: this.#fontColor,
        fontSize: this.#fontSize ? `calc(${this.#fontSize}px * var(--total-scale-factor))` : ""
      }
    };
    for (const line of text.split("\n")) {
      popupLines.push({
        name: "span",
        value: line,
        attributes: lineAttributes
      });
    }
    return popupContent;
  }
  #keyDown(event) {
    if (event.altKey || event.shiftKey || event.ctrlKey || event.metaKey) {
      return;
    }
    if (event.key === "Enter" || event.key === "Escape" && this.#pinned) {
      this.#toggle();
    }
  }
  updateEdited({
    rect,
    popup,
    deleted
  }) {
    if (this.#commentManager) {
      if (deleted) {
        this.remove();
        this.#commentText = null;
      } else if (popup) {
        if (popup.deleted) {
          this.remove();
        } else {
          this.#updateColor();
          this.#commentText = popup.text;
        }
      }
      if (rect) {
        this.#commentButtonPosition = null;
        this.#setCommentButtonPosition();
        this.#updateCommentButtonPosition();
      }
      return;
    }
    if (deleted || popup?.deleted) {
      this.remove();
      return;
    }
    this.#addEventListeners();
    this.#updates ||= {
      contentsObj: this.#contentsObj,
      richText: this.#richText
    };
    if (rect) {
      this.#position = null;
    }
    if (popup && popup.text) {
      this.#richText = this.#makePopupContent(popup.text);
      this.#dateObj = PDFDateString.toDateObject(popup.date);
      this.#contentsObj = null;
    }
    this.#popup?.remove();
    this.#popup = null;
  }
  resetEdited() {
    if (!this.#updates) {
      return;
    }
    ({
      contentsObj: this.#contentsObj,
      richText: this.#richText
    } = this.#updates);
    this.#updates = null;
    this.#popup?.remove();
    this.#popup = null;
    this.#position = null;
  }
  remove() {
    this.#popupAbortController?.abort();
    this.#popupAbortController = null;
    this.#popup?.remove();
    this.#popup = null;
    this.#wasVisible = false;
    this.#pinned = false;
    this.#commentButton?.remove();
    this.#commentButton = null;
    if (this.trigger) {
      for (const element of this.trigger) {
        element.classList.remove("popupTriggerArea");
      }
    }
  }
  #setPosition() {
    if (this.#position !== null) {
      return;
    }
    const {
      page: {
        view
      },
      viewport: {
        rawDims: {
          pageWidth,
          pageHeight,
          pageX,
          pageY
        }
      }
    } = this.#parent;
    let useParentRect = !!this.#parentRect;
    let rect = useParentRect ? this.#parentRect : this.#rect;
    for (const element of this.#elements) {
      if (!rect || Util.intersect(element.data.rect, rect) !== null) {
        rect = element.data.rect;
        useParentRect = true;
        break;
      }
    }
    const normalizedRect = Util.normalizeRect([rect[0], view[3] - rect[1] + view[1], rect[2], view[3] - rect[3] + view[1]]);
    const HORIZONTAL_SPACE_AFTER_ANNOTATION = 5;
    const parentWidth = useParentRect ? rect[2] - rect[0] + HORIZONTAL_SPACE_AFTER_ANNOTATION : 0;
    const popupLeft = normalizedRect[0] + parentWidth;
    const popupTop = normalizedRect[1];
    this.#position = [100 * (popupLeft - pageX) / pageWidth, 100 * (popupTop - pageY) / pageHeight];
    const {
      style
    } = this.#container;
    style.left = `${this.#position[0]}%`;
    style.top = `${this.#position[1]}%`;
  }
  #toggle() {
    if (this.#commentManager) {
      this.#commentManager.toggleCommentPopup(this, false);
      return;
    }
    this.#pinned = !this.#pinned;
    if (this.#pinned) {
      this.#show();
      this.#container.addEventListener("click", this.#boundToggle);
      this.#container.addEventListener("keydown", this.#boundKeyDown);
    } else {
      this.#hide();
      this.#container.removeEventListener("click", this.#boundToggle);
      this.#container.removeEventListener("keydown", this.#boundKeyDown);
    }
  }
  #show() {
    if (!this.#popup) {
      this.render();
    }
    if (!this.isVisible) {
      this.#setPosition();
      this.#container.hidden = false;
      this.#container.style.zIndex = parseInt(this.#container.style.zIndex, 10) + 1000;
    } else if (this.#pinned) {
      this.#container.classList.add("focused");
    }
  }
  #hide() {
    this.#container.classList.remove("focused");
    if (this.#pinned || !this.isVisible) {
      return;
    }
    this.#container.hidden = true;
    this.#container.style.zIndex = parseInt(this.#container.style.zIndex, 10) - 1000;
  }
  forceHide() {
    this.#wasVisible = this.isVisible;
    if (!this.#wasVisible) {
      return;
    }
    this.#container.hidden = true;
  }
  maybeShow() {
    if (this.#commentManager) {
      return;
    }
    this.#addEventListeners();
    if (!this.#wasVisible) {
      return;
    }
    if (!this.#popup) {
      this.#show();
    }
    this.#wasVisible = false;
    this.#container.hidden = false;
  }
  get isVisible() {
    return !this.#commentManager && this.#container.hidden === false;
  }
}
class FreeTextAnnotationElement extends AnnotationElement {
  constructor(parameters) {
    super(parameters, {
      isRenderable: true,
      ignoreBorder: true
    });
    this.textContent = parameters.data.textContent;
    this.textPosition = parameters.data.textPosition;
    this.annotationEditorType = AnnotationEditorType.FREETEXT;
  }
  render() {
    this.container.classList.add("freeTextAnnotation");
    if (this.textContent) {
      const content = this.contentElement = document.createElement("div");
      content.classList.add("annotationTextContent");
      content.setAttribute("role", "comment");
      for (const line of this.textContent) {
        const lineSpan = document.createElement("span");
        lineSpan.textContent = line;
        content.append(lineSpan);
      }
      this.container.append(content);
    }
    if (!this.data.popupRef && this.hasPopupData) {
      this.hasOwnCommentButton = true;
      this._createPopup();
    }
    this._editOnDoubleClick();
    return this.container;
  }
}
class LineAnnotationElement extends AnnotationElement {
  #line = null;
  constructor(parameters) {
    super(parameters, {
      isRenderable: true,
      ignoreBorder: true
    });
  }
  render() {
    this.container.classList.add("lineAnnotation");
    const {
      data,
      width,
      height
    } = this;
    const svgFactory = AnnotationElement._svgFactory;
    const svg = svgFactory.create(width, height, true);
    const line = this.#line = svgFactory.createElement("svg:line");
    line.setAttribute("x1", data.rect[2] - data.lineCoordinates[0]);
    line.setAttribute("y1", data.rect[3] - data.lineCoordinates[1]);
    line.setAttribute("x2", data.rect[2] - data.lineCoordinates[2]);
    line.setAttribute("y2", data.rect[3] - data.lineCoordinates[3]);
    line.setAttribute("stroke-width", data.borderStyle.width || 1);
    line.setAttribute("stroke", "transparent");
    line.setAttribute("fill", "transparent");
    svg.append(line);
    this.container.append(svg);
    if (!data.popupRef && this.hasPopupData) {
      this.hasOwnCommentButton = true;
      this._createPopup();
    }
    return this.container;
  }
  getElementsToTriggerPopup() {
    return this.#line;
  }
  addHighlightArea() {
    this.container.classList.add("highlightArea");
  }
}
class SquareAnnotationElement extends AnnotationElement {
  #square = null;
  constructor(parameters) {
    super(parameters, {
      isRenderable: true,
      ignoreBorder: true
    });
  }
  render() {
    this.container.classList.add("squareAnnotation");
    const {
      data,
      width,
      height
    } = this;
    const svgFactory = AnnotationElement._svgFactory;
    const svg = svgFactory.create(width, height, true);
    const borderWidth = data.borderStyle.width;
    const square = this.#square = svgFactory.createElement("svg:rect");
    square.setAttribute("x", borderWidth / 2);
    square.setAttribute("y", borderWidth / 2);
    square.setAttribute("width", width - borderWidth);
    square.setAttribute("height", height - borderWidth);
    square.setAttribute("stroke-width", borderWidth || 1);
    square.setAttribute("stroke", "transparent");
    square.setAttribute("fill", "transparent");
    svg.append(square);
    this.container.append(svg);
    if (!data.popupRef && this.hasPopupData) {
      this.hasOwnCommentButton = true;
      this._createPopup();
    }
    return this.container;
  }
  getElementsToTriggerPopup() {
    return this.#square;
  }
  addHighlightArea() {
    this.container.classList.add("highlightArea");
  }
}
class CircleAnnotationElement extends AnnotationElement {
  #circle = null;
  constructor(parameters) {
    super(parameters, {
      isRenderable: true,
      ignoreBorder: true
    });
  }
  render() {
    this.container.classList.add("circleAnnotation");
    const {
      data,
      width,
      height
    } = this;
    const svgFactory = AnnotationElement._svgFactory;
    const svg = svgFactory.create(width, height, true);
    const borderWidth = data.borderStyle.width;
    const circle = this.#circle = svgFactory.createElement("svg:ellipse");
    circle.setAttribute("cx", width / 2);
    circle.setAttribute("cy", height / 2);
    circle.setAttribute("rx", width / 2 - borderWidth / 2);
    circle.setAttribute("ry", height / 2 - borderWidth / 2);
    circle.setAttribute("stroke-width", borderWidth || 1);
    circle.setAttribute("stroke", "transparent");
    circle.setAttribute("fill", "transparent");
    svg.append(circle);
    this.container.append(svg);
    if (!data.popupRef && this.hasPopupData) {
      this.hasOwnCommentButton = true;
      this._createPopup();
    }
    return this.container;
  }
  getElementsToTriggerPopup() {
    return this.#circle;
  }
  addHighlightArea() {
    this.container.classList.add("highlightArea");
  }
}
class PolylineAnnotationElement extends AnnotationElement {
  #polyline = null;
  constructor(parameters) {
    super(parameters, {
      isRenderable: true,
      ignoreBorder: true
    });
    this.containerClassName = "polylineAnnotation";
    this.svgElementName = "svg:polyline";
  }
  render() {
    this.container.classList.add(this.containerClassName);
    const {
      data: {
        rect,
        vertices,
        borderStyle,
        popupRef
      },
      width,
      height
    } = this;
    if (!vertices) {
      return this.container;
    }
    const svgFactory = AnnotationElement._svgFactory;
    const svg = svgFactory.create(width, height, true);
    let points = [];
    for (let i = 0, ii = vertices.length; i < ii; i += 2) {
      const x = vertices[i] - rect[0];
      const y = rect[3] - vertices[i + 1];
      points.push(`${x},${y}`);
    }
    points = points.join(" ");
    const polyline = this.#polyline = svgFactory.createElement(this.svgElementName);
    polyline.setAttribute("points", points);
    polyline.setAttribute("stroke-width", borderStyle.width || 1);
    polyline.setAttribute("stroke", "transparent");
    polyline.setAttribute("fill", "transparent");
    svg.append(polyline);
    this.container.append(svg);
    if (!popupRef && this.hasPopupData) {
      this.hasOwnCommentButton = true;
      this._createPopup();
    }
    return this.container;
  }
  getElementsToTriggerPopup() {
    return this.#polyline;
  }
  addHighlightArea() {
    this.container.classList.add("highlightArea");
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
    super(parameters, {
      isRenderable: true,
      ignoreBorder: true
    });
  }
  render() {
    this.container.classList.add("caretAnnotation");
    if (!this.data.popupRef && this.hasPopupData) {
      this.hasOwnCommentButton = true;
      this._createPopup();
    }
    return this.container;
  }
}
class InkAnnotationElement extends AnnotationElement {
  #polylinesGroupElement = null;
  #polylines = [];
  constructor(parameters) {
    super(parameters, {
      isRenderable: true,
      ignoreBorder: true
    });
    this.containerClassName = "inkAnnotation";
    this.svgElementName = "svg:polyline";
    this.annotationEditorType = this.data.it === "InkHighlight" ? AnnotationEditorType.HIGHLIGHT : AnnotationEditorType.INK;
  }
  #getTransform(rotation, rect) {
    switch (rotation) {
      case 90:
        return {
          transform: `rotate(90) translate(${-rect[0]},${rect[1]}) scale(1,-1)`,
          width: rect[3] - rect[1],
          height: rect[2] - rect[0]
        };
      case 180:
        return {
          transform: `rotate(180) translate(${-rect[2]},${rect[1]}) scale(1,-1)`,
          width: rect[2] - rect[0],
          height: rect[3] - rect[1]
        };
      case 270:
        return {
          transform: `rotate(270) translate(${-rect[2]},${rect[3]}) scale(1,-1)`,
          width: rect[3] - rect[1],
          height: rect[2] - rect[0]
        };
      default:
        return {
          transform: `translate(${-rect[0]},${rect[3]}) scale(1,-1)`,
          width: rect[2] - rect[0],
          height: rect[3] - rect[1]
        };
    }
  }
  render() {
    this.container.classList.add(this.containerClassName);
    const {
      data: {
        rect,
        rotation,
        inkLists,
        borderStyle,
        popupRef
      }
    } = this;
    const {
      transform,
      width,
      height
    } = this.#getTransform(rotation, rect);
    const svgFactory = AnnotationElement._svgFactory;
    const svg = svgFactory.create(width, height, true);
    const g = this.#polylinesGroupElement = svgFactory.createElement("svg:g");
    svg.append(g);
    g.setAttribute("stroke-width", borderStyle.width || 1);
    g.setAttribute("stroke-linecap", "round");
    g.setAttribute("stroke-linejoin", "round");
    g.setAttribute("stroke-miterlimit", 10);
    g.setAttribute("stroke", "transparent");
    g.setAttribute("fill", "transparent");
    g.setAttribute("transform", transform);
    for (const inkList of inkLists) {
      const polyline = svgFactory.createElement(this.svgElementName);
      this.#polylines.push(polyline);
      polyline.setAttribute("points", inkList.join(","));
      g.append(polyline);
    }
    if (!popupRef && this.hasPopupData) {
      this.hasOwnCommentButton = true;
      this._createPopup();
    }
    this.container.append(svg);
    this._editOnDoubleClick();
    return this.container;
  }
  updateEdited(params) {
    super.updateEdited(params);
    const {
      thickness,
      points,
      rect
    } = params;
    const g = this.#polylinesGroupElement;
    if (thickness >= 0) {
      g.setAttribute("stroke-width", thickness || 1);
    }
    if (points) {
      for (let i = 0, ii = this.#polylines.length; i < ii; i++) {
        this.#polylines[i].setAttribute("points", points[i].join(","));
      }
    }
    if (rect) {
      const {
        transform,
        width,
        height
      } = this.#getTransform(this.data.rotation, rect);
      const root = g.parentElement;
      root.setAttribute("viewBox", `0 0 ${width} ${height}`);
      g.setAttribute("transform", transform);
    }
  }
  getElementsToTriggerPopup() {
    return this.#polylines;
  }
  addHighlightArea() {
    this.container.classList.add("highlightArea");
  }
}
class HighlightAnnotationElement extends AnnotationElement {
  constructor(parameters) {
    super(parameters, {
      isRenderable: true,
      ignoreBorder: true,
      createQuadrilaterals: true
    });
    this.annotationEditorType = AnnotationEditorType.HIGHLIGHT;
  }
  render() {
    const {
      data: {
        overlaidText,
        popupRef
      }
    } = this;
    if (!popupRef && this.hasPopupData) {
      this.hasOwnCommentButton = true;
      this._createPopup();
    }
    this.container.classList.add("highlightAnnotation");
    this._editOnDoubleClick();
    if (overlaidText) {
      const mark = document.createElement("mark");
      mark.classList.add("overlaidText");
      mark.textContent = overlaidText;
      this.container.append(mark);
    }
    return this.container;
  }
}
class UnderlineAnnotationElement extends AnnotationElement {
  constructor(parameters) {
    super(parameters, {
      isRenderable: true,
      ignoreBorder: true,
      createQuadrilaterals: true
    });
  }
  render() {
    const {
      data: {
        overlaidText,
        popupRef
      }
    } = this;
    if (!popupRef && this.hasPopupData) {
      this.hasOwnCommentButton = true;
      this._createPopup();
    }
    this.container.classList.add("underlineAnnotation");
    if (overlaidText) {
      const underline = document.createElement("u");
      underline.classList.add("overlaidText");
      underline.textContent = overlaidText;
      this.container.append(underline);
    }
    return this.container;
  }
}
class SquigglyAnnotationElement extends AnnotationElement {
  constructor(parameters) {
    super(parameters, {
      isRenderable: true,
      ignoreBorder: true,
      createQuadrilaterals: true
    });
  }
  render() {
    const {
      data: {
        overlaidText,
        popupRef
      }
    } = this;
    if (!popupRef && this.hasPopupData) {
      this.hasOwnCommentButton = true;
      this._createPopup();
    }
    this.container.classList.add("squigglyAnnotation");
    if (overlaidText) {
      const underline = document.createElement("u");
      underline.classList.add("overlaidText");
      underline.textContent = overlaidText;
      this.container.append(underline);
    }
    return this.container;
  }
}
class StrikeOutAnnotationElement extends AnnotationElement {
  constructor(parameters) {
    super(parameters, {
      isRenderable: true,
      ignoreBorder: true,
      createQuadrilaterals: true
    });
  }
  render() {
    const {
      data: {
        overlaidText,
        popupRef
      }
    } = this;
    if (!popupRef && this.hasPopupData) {
      this.hasOwnCommentButton = true;
      this._createPopup();
    }
    this.container.classList.add("strikeoutAnnotation");
    if (overlaidText) {
      const strikeout = document.createElement("s");
      strikeout.classList.add("overlaidText");
      strikeout.textContent = overlaidText;
      this.container.append(strikeout);
    }
    return this.container;
  }
}
class StampAnnotationElement extends AnnotationElement {
  constructor(parameters) {
    super(parameters, {
      isRenderable: true,
      ignoreBorder: true
    });
    this.annotationEditorType = AnnotationEditorType.STAMP;
  }
  render() {
    this.container.classList.add("stampAnnotation");
    this.container.setAttribute("role", "img");
    if (!this.data.popupRef && this.hasPopupData) {
      this.hasOwnCommentButton = true;
      this._createPopup();
    }
    this._editOnDoubleClick();
    return this.container;
  }
}
class FileAttachmentAnnotationElement extends AnnotationElement {
  #trigger = null;
  constructor(parameters) {
    super(parameters, {
      isRenderable: true
    });
    const {
      fileId,
      file
    } = this.data;
    this.filename = file.filename;
    this.content = file.content;
    this.fileId = fileId;
    this.linkService.eventBus?.dispatch("fileattachmentannotation", {
      source: this,
      attachmentId: this.fileId,
      ...file
    });
  }
  render() {
    this.container.classList.add("fileAttachmentAnnotation");
    const {
      container,
      data
    } = this;
    let trigger;
    if (data.hasAppearance || data.fillAlpha === 0) {
      trigger = document.createElement("div");
    } else {
      trigger = document.createElement("img");
      trigger.src = `${this.imageResourcesPath}annotation-${/paperclip/i.test(data.name) ? "paperclip" : "pushpin"}.svg`;
      if (data.fillAlpha && data.fillAlpha < 1) {
        trigger.style = `filter: opacity(${Math.round(data.fillAlpha * 100)}%);`;
      }
    }
    trigger.addEventListener("dblclick", this.#download.bind(this));
    this.#trigger = trigger;
    const {
      isMac
    } = FeatureTest.platform;
    container.addEventListener("keydown", evt => {
      if (evt.key === "Enter" && (isMac ? evt.metaKey : evt.ctrlKey)) {
        this.#download();
      }
    });
    if (!data.popupRef && this.hasPopupData) {
      this.hasOwnCommentButton = true;
      this._createPopup();
    } else {
      trigger.classList.add("popupTriggerArea");
    }
    container.append(trigger);
    return container;
  }
  getElementsToTriggerPopup() {
    return this.#trigger;
  }
  addHighlightArea() {
    this.container.classList.add("highlightArea");
  }
  async #download() {
    const {
      fileId,
      filename,
      content: fallbackContent
    } = this;
    const content = (await this.linkService.getAttachmentContent(fileId)) || fallbackContent;
    if (content) {
      this.downloadManager?.openOrDownloadData(content, filename);
    }
  }
}
class MediaAnnotationElement extends AnnotationElement {
  #abortController = new AbortController();
  #contentUrl = null;
  #media = null;
  constructor(parameters) {
    super(parameters, {
      isRenderable: !!parameters.data.richMedia
    });
  }
  render() {
    this.container.classList.add("mediaAnnotation");
    const {
      filename
    } = this.data.richMedia;
    const button = document.createElement("button");
    button.className = "mediaPlayButton";
    button.type = "button";
    button.title = button.ariaLabel = filename;
    button.addEventListener("click", () => this.#load(button), {
      signal: this.#abortController.signal
    });
    this.container.append(button);
    return this.container;
  }
  async #load(button) {
    const {
      fileId,
      filename,
      contentType
    } = this.data.richMedia;
    button.disabled = true;
    let content;
    try {
      content = await this.linkService.getAttachmentContent(fileId);
    } catch {
      return;
    } finally {
      button.disabled = false;
    }
    if (!content || !button.isConnected) {
      return;
    }
    const {
      signal
    } = this.#abortController;
    const blob = new Blob([content], {
      type: contentType
    });
    if (!/^(?:video|audio)\//.test(blob.type)) {
      return;
    }
    const url = URL.createObjectURL(blob);
    this.#contentUrl = url;
    const isAudio = blob.type.startsWith("audio/");
    const media = document.createElement(isAudio ? "audio" : "video");
    this.#media = media;
    media.className = "mediaContent";
    this._setBackgroundColor(media);
    media.src = url;
    media.title = filename;
    media.controls = true;
    media.autoplay = true;
    media.tabIndex = 0;
    if (isAudio) {
      let hovered = false;
      let focused = false;
      const updateControls = () => {
        media.controls = hovered || focused;
      };
      this.container.addEventListener("pointerenter", () => {
        hovered = true;
        updateControls();
      }, {
        signal
      });
      this.container.addEventListener("pointerleave", () => {
        hovered = false;
        updateControls();
      }, {
        signal
      });
      this.container.addEventListener("focusin", () => {
        focused = true;
        updateControls();
      }, {
        signal
      });
      this.container.addEventListener("focusout", () => {
        focused = false;
        updateControls();
      }, {
        signal
      });
    }
    media.addEventListener("emptied", () => this.#revokeContentUrl(url), {
      once: true,
      signal
    });
    button.replaceWith(media);
    media.play().catch(() => {});
  }
  #revokeContentUrl(url = this.#contentUrl) {
    if (url && url === this.#contentUrl) {
      URL.revokeObjectURL(url);
      this.#contentUrl = null;
    }
  }
  destroy() {
    this.#abortController.abort();
    if (this.#media) {
      this.#media.pause();
      this.#media.removeAttribute("src");
      this.#media.load();
      this.#media = null;
    }
    this.#revokeContentUrl();
  }
}
class AnnotationLayer {
  #accessibilityManager = null;
  #annotationCanvasMap = null;
  #annotationStorage = null;
  #editableAnnotations = new Map();
  #structTreeLayer = null;
  #linkService = null;
  #elements = [];
  #hasAriaAttributesFromStructTree = false;
  zIndex = 0;
  constructor({
    div,
    accessibilityManager,
    annotationCanvasMap,
    annotationEditorUIManager,
    page,
    viewport,
    structTreeLayer,
    commentManager,
    linkService,
    annotationStorage
  }) {
    this.div = div;
    this.#accessibilityManager = accessibilityManager;
    this.#annotationCanvasMap = annotationCanvasMap;
    this.#structTreeLayer = structTreeLayer || null;
    this.#linkService = linkService || null;
    this.#annotationStorage = annotationStorage || new AnnotationStorage();
    this.page = page;
    this.viewport = viewport;
    this._annotationEditorUIManager = annotationEditorUIManager;
    this._commentManager = commentManager || null;
  }
  hasEditableAnnotations() {
    return this.#editableAnnotations.size > 0;
  }
  async render(params) {
    const {
      annotations,
      optionalContentConfig
    } = params;
    const layer = this.div;
    setLayerDimensions(layer, this.viewport);
    const popupToElements = new Map();
    const popupAnnotations = [];
    const elementParams = {
      data: null,
      layer,
      linkService: this.#linkService,
      downloadManager: params.downloadManager,
      imageResourcesPath: params.imageResourcesPath || "",
      renderForms: params.renderForms !== false,
      annotationStorage: this.#annotationStorage,
      enableComment: params.enableComment === true,
      enableAnnotationEditing: params.enableAnnotationEditing !== false,
      enableScripting: params.enableScripting === true,
      hasJSActions: params.hasJSActions,
      fieldObjects: params.fieldObjects,
      parent: this,
      elements: null
    };
    for (const data of annotations) {
      if (data.noHTML) {
        continue;
      }
      const isPopupAnnotation = data.annotationType === AnnotationType.POPUP;
      if (!isPopupAnnotation) {
        if (data.rect[2] === data.rect[0] || data.rect[3] === data.rect[1]) {
          continue;
        }
      } else {
        const elements = popupToElements.get(data.id);
        if (!elements) {
          continue;
        }
        if (!this._commentManager) {
          popupAnnotations.push(data);
          continue;
        }
        elementParams.elements = elements;
      }
      elementParams.data = data;
      const element = AnnotationElementFactory.create(elementParams);
      if (!element.isRenderable) {
        continue;
      }
      if (!isPopupAnnotation) {
        this.#elements.push(element);
        if (data.popupRef) {
          popupToElements.getOrInsertComputed(data.popupRef, makeArr).push(element);
        }
      }
      const rendered = element.render();
      if (data.hidden) {
        rendered.style.visibility = "hidden";
      }
      element.updateOC(optionalContentConfig);
      if (element._isEditable) {
        this.#editableAnnotations.set(element.data.id, element);
        this._annotationEditorUIManager?.renderAnnotationElement(element);
      }
    }
    await this.#addElementsToDOM();
    for (const data of popupAnnotations) {
      const elements = elementParams.elements = popupToElements.get(data.id);
      elementParams.data = data;
      const element = AnnotationElementFactory.create(elementParams);
      if (!element.isRenderable) {
        continue;
      }
      const rendered = element.render();
      element.contentElement.id = `${AnnotationPrefix}${data.id}`;
      if (data.hidden) {
        rendered.style.visibility = "hidden";
      }
      elements.at(-1).container.after(rendered);
    }
    this.#setAnnotationCanvasMap();
  }
  async #addElementsToDOM() {
    if (this.#elements.length === 0) {
      return;
    }
    this.div.replaceChildren();
    const promises = [];
    if (!this.#hasAriaAttributesFromStructTree) {
      this.#hasAriaAttributesFromStructTree = true;
      for (const {
        contentElement,
        data: {
          hidden,
          id,
          oc
        }
      } of this.#elements) {
        const annotationId = contentElement.id = `${AnnotationPrefix}${id}`;
        const enableLinkOwnership = contentElement.localName === "a" && !hidden && !oc;
        promises.push(this.#structTreeLayer?.getAriaAttributes(annotationId, {
          enableLinkOwnership
        }).then(ariaAttributes => {
          if (ariaAttributes) {
            for (const [key, value] of ariaAttributes) {
              contentElement.setAttribute(key, value);
            }
          }
        }));
      }
    }
    this.#elements.sort(({
      data: {
        rect: [a0, a1, a2, a3]
      }
    }, {
      data: {
        rect: [b0, b1, b2, b3]
      }
    }) => {
      if (a0 === a2 && a1 === a3) {
        return +1;
      }
      if (b0 === b2 && b1 === b3) {
        return -1;
      }
      const top1 = a3;
      const bot1 = a1;
      const mid1 = (a1 + a3) / 2;
      const top2 = b3;
      const bot2 = b1;
      const mid2 = (b1 + b3) / 2;
      if (mid1 >= top2 && mid2 <= bot1) {
        return -1;
      }
      if (mid2 >= top1 && mid1 <= bot2) {
        return +1;
      }
      const centerX1 = (a0 + a2) / 2;
      const centerX2 = (b0 + b2) / 2;
      return centerX1 - centerX2;
    });
    const fragment = document.createDocumentFragment();
    for (const element of this.#elements) {
      fragment.append(element.container);
      if (this._commentManager) {
        (element.extraPopupElement?.popup || element.popup)?.renderCommentButton();
      } else if (element.extraPopupElement) {
        fragment.append(element.extraPopupElement.render());
      }
    }
    this.div.append(fragment);
    await Promise.all(promises);
    if (this.#accessibilityManager) {
      const annotationIds = await this.#structTreeLayer?.getAnnotationIds();
      for (const {
        contentElement
      } of this.#elements) {
        if (annotationIds?.has(contentElement.id)) {
          continue;
        }
        this.#accessibilityManager.addPointerInTextLayer(contentElement, false);
      }
    }
  }
  async addLinkAnnotations(annotations) {
    const elementParams = {
      data: null,
      layer: this.div,
      linkService: this.#linkService,
      parent: this
    };
    for (const data of annotations) {
      data.borderStyle ||= AnnotationLayer._defaultBorderStyle;
      elementParams.data = data;
      const element = AnnotationElementFactory.create(elementParams);
      if (!element.isRenderable) {
        continue;
      }
      element.render();
      element.contentElement.id = `${AnnotationPrefix}${data.id}`;
      this.#elements.push(element);
    }
    await this.#addElementsToDOM();
  }
  update({
    viewport,
    optionalContentConfig
  }) {
    const layer = this.div;
    this.viewport = viewport;
    setLayerDimensions(layer, {
      rotation: viewport.rotation
    });
    for (const element of this.#elements) {
      element.updateOC(optionalContentConfig);
    }
    this.#setAnnotationCanvasMap();
    layer.hidden = false;
  }
  destroy() {
    for (const element of this.#elements) {
      element.destroy?.();
      this.#accessibilityManager?.removePointerInTextLayer(element.contentElement);
    }
    this.#elements.length = 0;
    this.#editableAnnotations.clear();
    this.div.replaceChildren();
  }
  #setAnnotationCanvasMap() {
    if (!this.#annotationCanvasMap) {
      return;
    }
    const layer = this.div;
    for (const [id, canvas] of this.#annotationCanvasMap) {
      const element = layer.querySelector(`[data-annotation-id="${id}"]`);
      if (!element) {
        continue;
      }
      if (Array.isArray(canvas)) {
        for (const cvs of canvas) {
          cvs.className = "annotationContent";
          cvs.ariaHidden = true;
        }
      } else {
        canvas.className = "annotationContent";
        canvas.ariaHidden = true;
      }
      const toRemove = [];
      for (const child of element.children) {
        if (child.nodeName === "CANVAS") {
          toRemove.push(child);
        }
      }
      for (const child of toRemove) {
        child.remove();
      }
      const firstCanvas = Array.isArray(canvas) ? canvas[0] : canvas;
      const {
        firstChild
      } = element;
      if (!firstChild) {
        element.append(firstCanvas);
      } else if (!firstChild.classList.contains("annotationContent")) {
        firstChild.before(firstCanvas);
      } else {
        firstChild.after(firstCanvas);
      }
      if (Array.isArray(canvas)) {
        let lastCanvas = firstCanvas;
        for (let i = 1, ii = canvas.length; i < ii; i++) {
          lastCanvas.after(canvas[i]);
          lastCanvas = canvas[i];
        }
      }
      this.#annotationCanvasMap.delete(id);
      const editableAnnotation = this.#editableAnnotations.get(id);
      if (!editableAnnotation) {
        continue;
      }
      if (editableAnnotation._hasNoCanvas) {
        this._annotationEditorUIManager?.setMissingCanvas(id, element.id, canvas);
        editableAnnotation._hasNoCanvas = false;
      } else {
        editableAnnotation.canvas = canvas;
      }
    }
  }
  refreshCanvases() {
    this.#setAnnotationCanvasMap();
  }
  getEditableAnnotations() {
    return this.#editableAnnotations.values();
  }
  getEditableAnnotation(id) {
    return this.#editableAnnotations.get(id);
  }
  addFakeAnnotation(editor) {
    const {
      div
    } = this;
    const {
      id,
      rotation
    } = editor;
    const element = new EditorAnnotationElement({
      data: {
        id,
        rect: editor.getPDFRect(),
        rotation
      },
      editor,
      layer: div,
      parent: this,
      enableComment: !!this._commentManager,
      linkService: this.#linkService,
      annotationStorage: this.#annotationStorage
    });
    element.render();
    element.contentElement.id = `${AnnotationPrefix}${id}`;
    element.createOrUpdatePopup();
    this.#elements.push(element);
    return element;
  }
  removeAnnotation(id) {
    const index = this.#elements.findIndex(el => el.data.id === id);
    if (index < 0) {
      return;
    }
    const [element] = this.#elements.splice(index, 1);
    this.#accessibilityManager?.removePointerInTextLayer(element.contentElement);
  }
  updateFakeAnnotations(editors) {
    if (editors.length === 0) {
      return;
    }
    for (const editor of editors) {
      editor.updateFakeAnnotationElement(this);
    }
    this.#addElementsToDOM();
  }
  togglePointerEvents(enabled = false) {
    this.div.classList.toggle("disabled", !enabled);
  }
  static get _defaultBorderStyle() {
    return shadow(this, "_defaultBorderStyle", Object.freeze({
      width: 1,
      rawWidth: 1,
      style: AnnotationBorderStyleType.SOLID,
      dashArray: [3],
      horizontalCornerRadius: 0,
      verticalCornerRadius: 0
    }));
  }
}

;// ./src/display/editor/freetext.js





const EOL_PATTERN = /\r\n?|\n/g;
class FreeTextEditor extends AnnotationEditor {
  #content = "";
  #editorDivId = `${this.id}-editor`;
  #editModeAC = null;
  #fontSize;
  _colorPicker = null;
  static _freeTextDefaultContent = "";
  static _internalPadding = 0;
  static _defaultColor = null;
  static _defaultFontSize = 10;
  static get _keyboardManager() {
    const proto = FreeTextEditor.prototype;
    const arrowChecker = self => self.isEmpty();
    const small = AnnotationEditorUIManager.TRANSLATE_SMALL;
    const big = AnnotationEditorUIManager.TRANSLATE_BIG;
    return shadow(this, "_keyboardManager", new KeyboardManager([[["ctrl+s", "mac+meta+s", "ctrl+p", "mac+meta+p"], proto.commitOrRemove, {
      bubbles: true
    }], [["ctrl+Enter", "mac+meta+Enter"], proto.commitOrRemove], [["Escape"], proto.commitOrRemove], [["ArrowLeft"], proto._translateEmpty, {
      args: [-small, 0],
      checker: arrowChecker
    }], [["ctrl+ArrowLeft", "mac+shift+ArrowLeft"], proto._translateEmpty, {
      args: [-big, 0],
      checker: arrowChecker
    }], [["ArrowRight"], proto._translateEmpty, {
      args: [small, 0],
      checker: arrowChecker
    }], [["ctrl+ArrowRight", "mac+shift+ArrowRight"], proto._translateEmpty, {
      args: [big, 0],
      checker: arrowChecker
    }], [["ArrowUp"], proto._translateEmpty, {
      args: [0, -small],
      checker: arrowChecker
    }], [["ctrl+ArrowUp", "mac+shift+ArrowUp"], proto._translateEmpty, {
      args: [0, -big],
      checker: arrowChecker
    }], [["ArrowDown"], proto._translateEmpty, {
      args: [0, small],
      checker: arrowChecker
    }], [["ctrl+ArrowDown", "mac+shift+ArrowDown"], proto._translateEmpty, {
      args: [0, big],
      checker: arrowChecker
    }]]));
  }
  static _type = "freetext";
  static _editorType = AnnotationEditorType.FREETEXT;
  constructor(params) {
    super({
      ...params,
      name: "freeTextEditor"
    });
    this.color = params.color || FreeTextEditor._defaultColor || AnnotationEditor._defaultLineColor;
    this.#fontSize = params.fontSize || FreeTextEditor._defaultFontSize;
    if (!this.annotationElementId) {
      this._uiManager.a11yAlert(AnnotationEditor._l10nAlert.freetext);
    }
    this.canAddComment = false;
  }
  static initialize(l10n, uiManager) {
    AnnotationEditor.initialize(l10n, uiManager);
    const style = getComputedStyle(document.documentElement);
    this._internalPadding = parseFloat(style.getPropertyValue("--freetext-padding"));
  }
  static updateDefaultParams(type, value) {
    switch (type) {
      case AnnotationEditorParamsType.FREETEXT_SIZE:
        FreeTextEditor._defaultFontSize = value;
        break;
      case AnnotationEditorParamsType.FREETEXT_COLOR:
        FreeTextEditor._defaultColor = value;
        break;
    }
  }
  updateParams(type, value) {
    switch (type) {
      case AnnotationEditorParamsType.FREETEXT_SIZE:
        this.#updateFontSize(value);
        break;
      case AnnotationEditorParamsType.FREETEXT_COLOR:
        this.#updateColor(value);
        break;
    }
  }
  static get defaultPropertiesToUpdate() {
    return [[AnnotationEditorParamsType.FREETEXT_SIZE, FreeTextEditor._defaultFontSize], [AnnotationEditorParamsType.FREETEXT_COLOR, FreeTextEditor._defaultColor || AnnotationEditor._defaultLineColor]];
  }
  get propertiesToUpdate() {
    return [[AnnotationEditorParamsType.FREETEXT_SIZE, this.#fontSize], [AnnotationEditorParamsType.FREETEXT_COLOR, this.color]];
  }
  get toolbarButtons() {
    this._colorPicker ||= new BasicColorPicker(this);
    return [["colorPicker", this._colorPicker]];
  }
  get colorType() {
    return AnnotationEditorParamsType.FREETEXT_COLOR;
  }
  #updateFontSize(fontSize) {
    const setFontsize = size => {
      this.editorDiv.style.fontSize = `calc(${size}px * var(--total-scale-factor))`;
      this.translate(0, -(size - this.#fontSize) * this.parentScale);
      this.#fontSize = size;
      this.#setEditorDimensions();
    };
    const savedFontsize = this.#fontSize;
    this.addCommands({
      cmd: setFontsize.bind(this, fontSize),
      undo: setFontsize.bind(this, savedFontsize),
      post: this._uiManager.updateUI.bind(this._uiManager, this),
      mustExec: true,
      type: AnnotationEditorParamsType.FREETEXT_SIZE,
      overwriteIfSameType: true,
      keepUndo: true
    });
  }
  onUpdatedColor() {
    this.editorDiv.style.color = this.color;
    this._colorPicker?.update(this.color);
    super.onUpdatedColor();
  }
  #updateColor(color) {
    const setColor = col => {
      this.color = col;
      this.onUpdatedColor();
    };
    const savedColor = this.color;
    this.addCommands({
      cmd: setColor.bind(this, color),
      undo: setColor.bind(this, savedColor),
      post: this._uiManager.updateUI.bind(this._uiManager, this),
      mustExec: true,
      type: AnnotationEditorParamsType.FREETEXT_COLOR,
      overwriteIfSameType: true,
      keepUndo: true
    });
  }
  _translateEmpty(x, y) {
    this._uiManager.translateSelectedEditors(x, y, true);
  }
  getInitialTranslation() {
    const scale = this.parentScale;
    return [-FreeTextEditor._internalPadding * scale, -(FreeTextEditor._internalPadding + this.#fontSize) * scale];
  }
  rebuild() {
    if (!this.parent) {
      return;
    }
    super.rebuild();
    if (this.div === null) {
      return;
    }
    if (!this.isAttachedToDOM) {
      this.parent.add(this);
    }
  }
  enableEditMode() {
    if (!super.enableEditMode()) {
      return false;
    }
    this.overlayDiv.classList.remove("enabled");
    this.editorDiv.contentEditable = true;
    this._isDraggable = false;
    this.div.removeAttribute("aria-activedescendant");
    this.#editModeAC = new AbortController();
    const signal = this._uiManager.combinedSignal(this.#editModeAC);
    this.editorDiv.addEventListener("keydown", this.editorDivKeydown.bind(this), {
      signal
    });
    this.editorDiv.addEventListener("focus", this.editorDivFocus.bind(this), {
      signal
    });
    this.editorDiv.addEventListener("blur", this.editorDivBlur.bind(this), {
      signal
    });
    this.editorDiv.addEventListener("input", this.editorDivInput.bind(this), {
      signal
    });
    this.editorDiv.addEventListener("paste", this.editorDivPaste.bind(this), {
      signal
    });
    return true;
  }
  disableEditMode() {
    if (!super.disableEditMode()) {
      return false;
    }
    this.overlayDiv.classList.add("enabled");
    this.editorDiv.contentEditable = false;
    this.div.setAttribute("aria-activedescendant", this.#editorDivId);
    this._isDraggable = true;
    this.#editModeAC?.abort();
    this.#editModeAC = null;
    this.div.focus({
      preventScroll: true
    });
    this.isEditing = false;
    this.parent.div.classList.add("freetextEditing");
    return true;
  }
  focusin(event) {
    if (!this._focusEventsAllowed) {
      return;
    }
    super.focusin(event);
    if (event.target !== this.editorDiv) {
      this.editorDiv.focus();
    }
  }
  onceAdded(focus) {
    if (this.width) {
      return;
    }
    this.enableEditMode();
    if (focus) {
      this.editorDiv.focus();
    }
    if (this._initialOptions?.isCentered) {
      this.center();
    }
    this._initialOptions = null;
  }
  isEmpty() {
    return !this.editorDiv || this.editorDiv.innerText.trim() === "";
  }
  remove() {
    this.isEditing = false;
    if (this.parent) {
      this.parent.setEditingState(true);
      this.parent.div.classList.add("freetextEditing");
    }
    super.remove();
  }
  #extractText() {
    const buffer = [];
    this.editorDiv.normalize();
    let prevChild = null;
    for (const child of this.editorDiv.childNodes) {
      if (prevChild?.nodeType === Node.TEXT_NODE && child.nodeName === "BR") {
        continue;
      }
      buffer.push(FreeTextEditor.#getNodeContent(child));
      prevChild = child;
    }
    return buffer.join("\n");
  }
  #setEditorDimensions() {
    const [parentWidth, parentHeight] = this.parentDimensions;
    let rect;
    if (this.isAttachedToDOM) {
      rect = this.div.getBoundingClientRect();
    } else {
      const {
        currentLayer,
        div
      } = this;
      const savedDisplay = div.style.display;
      const savedVisibility = div.classList.contains("hidden");
      div.classList.remove("hidden");
      div.style.display = "hidden";
      currentLayer.div.append(this.div);
      rect = div.getBoundingClientRect();
      div.remove();
      div.style.display = savedDisplay;
      div.classList.toggle("hidden", savedVisibility);
    }
    if (this.rotation % 180 === this.parentRotation % 180) {
      this.width = rect.width / parentWidth;
      this.height = rect.height / parentHeight;
    } else {
      this.width = rect.height / parentWidth;
      this.height = rect.width / parentHeight;
    }
    this.fixAndSetPosition();
  }
  commit() {
    if (!this.isInEditMode()) {
      return;
    }
    super.commit();
    this.disableEditMode();
    const savedText = this.#content;
    const newText = this.#content = this.#extractText().trimEnd();
    if (savedText === newText) {
      return;
    }
    const setText = text => {
      this.#content = text;
      if (!text) {
        this.remove();
        return;
      }
      this.#setContent();
      this._uiManager.rebuild(this);
      this.#setEditorDimensions();
    };
    this.addCommands({
      cmd: () => {
        setText(newText);
      },
      undo: () => {
        setText(savedText);
      },
      mustExec: false
    });
    this.#setEditorDimensions();
  }
  shouldGetKeyboardEvents() {
    return this.isInEditMode();
  }
  enterInEditMode() {
    this.enableEditMode();
    this.editorDiv.focus();
  }
  keydown(event) {
    if (event.target === this.div && event.key === "Enter") {
      this.enterInEditMode();
      event.preventDefault();
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
  editorDivInput(event) {
    this.parent.div.classList.toggle("freetextEditing", this.isEmpty());
  }
  disableEditing() {
    this.editorDiv.setAttribute("role", "comment");
    this.editorDiv.removeAttribute("aria-multiline");
  }
  enableEditing() {
    this.editorDiv.setAttribute("role", "textbox");
    this.editorDiv.setAttribute("aria-multiline", true);
  }
  get canChangeContent() {
    return true;
  }
  render() {
    if (this.div) {
      return this.div;
    }
    let baseX, baseY;
    if (this._isCopy || this.annotationElementId) {
      baseX = this.x;
      baseY = this.y;
    }
    super.render();
    this.editorDiv = document.createElement("div");
    this.editorDiv.className = "internal";
    this.editorDiv.setAttribute("id", this.#editorDivId);
    this.editorDiv.setAttribute("data-l10n-id", "pdfjs-free-text2");
    this.editorDiv.setAttribute("data-l10n-attrs", "default-content");
    this.enableEditing();
    this.editorDiv.contentEditable = true;
    const {
      style
    } = this.editorDiv;
    style.fontSize = `calc(${this.#fontSize}px * var(--total-scale-factor))`;
    style.color = this.color;
    this.div.append(this.editorDiv);
    this.overlayDiv = document.createElement("div");
    this.overlayDiv.classList.add("overlay", "enabled");
    this.div.append(this.overlayDiv);
    if (this._isCopy || this.annotationElementId) {
      const [parentWidth, parentHeight] = this.parentDimensions;
      if (this.annotationElementId) {
        const {
          position
        } = this._initialData;
        let [tx, ty] = this.getInitialTranslation();
        [tx, ty] = this.pageTranslationToScreen(tx, ty);
        const [pageWidth, pageHeight] = this.pageDimensions;
        const [pageX, pageY] = this.pageTranslation;
        let posX, posY;
        switch (this.rotation) {
          case 0:
            posX = baseX + (position[0] - pageX) / pageWidth;
            posY = baseY + this.height - (position[1] - pageY) / pageHeight;
            break;
          case 90:
            posX = baseX + (position[0] - pageX) / pageWidth;
            posY = baseY - (position[1] - pageY) / pageHeight;
            [tx, ty] = [ty, -tx];
            break;
          case 180:
            posX = baseX - this.width + (position[0] - pageX) / pageWidth;
            posY = baseY - (position[1] - pageY) / pageHeight;
            [tx, ty] = [-tx, -ty];
            break;
          case 270:
            posX = baseX + (position[0] - pageX - this.height * pageHeight) / pageWidth;
            posY = baseY + (position[1] - pageY - this.width * pageWidth) / pageHeight;
            [tx, ty] = [-ty, tx];
            break;
        }
        this.setAt(posX * parentWidth, posY * parentHeight, tx, ty);
      } else {
        this._moveAfterPaste(baseX, baseY);
      }
      this.#setContent();
      this._isDraggable = true;
      this.editorDiv.contentEditable = false;
    } else {
      this._isDraggable = false;
      this.editorDiv.contentEditable = true;
    }
    return this.div;
  }
  static #getNodeContent(node) {
    return (node.nodeType === Node.TEXT_NODE ? node.nodeValue : node.innerText).replaceAll(EOL_PATTERN, "");
  }
  editorDivPaste(event) {
    const clipboardData = event.clipboardData || window.clipboardData;
    const {
      types
    } = clipboardData;
    if (types.length === 1 && types[0] === "text/plain") {
      return;
    }
    event.preventDefault();
    const paste = FreeTextEditor.#deserializeContent(clipboardData.getData("text") || "").replaceAll(EOL_PATTERN, "\n");
    if (!paste) {
      return;
    }
    const selection = window.getSelection();
    if (!selection.rangeCount) {
      return;
    }
    this.editorDiv.normalize();
    selection.deleteFromDocument();
    const range = selection.getRangeAt(0);
    if (!paste.includes("\n")) {
      range.insertNode(document.createTextNode(paste));
      this.editorDiv.normalize();
      selection.collapseToStart();
      return;
    }
    const {
      startContainer,
      startOffset
    } = range;
    const bufferBefore = [];
    const bufferAfter = [];
    if (startContainer.nodeType === Node.TEXT_NODE) {
      const parent = startContainer.parentElement;
      bufferAfter.push(startContainer.nodeValue.slice(startOffset).replaceAll(EOL_PATTERN, ""));
      if (parent !== this.editorDiv) {
        let buffer = bufferBefore;
        for (const child of this.editorDiv.childNodes) {
          if (child === parent) {
            buffer = bufferAfter;
            continue;
          }
          buffer.push(FreeTextEditor.#getNodeContent(child));
        }
      }
      bufferBefore.push(startContainer.nodeValue.slice(0, startOffset).replaceAll(EOL_PATTERN, ""));
    } else if (startContainer === this.editorDiv) {
      let buffer = bufferBefore;
      let i = 0;
      for (const child of this.editorDiv.childNodes) {
        if (i++ === startOffset) {
          buffer = bufferAfter;
        }
        buffer.push(FreeTextEditor.#getNodeContent(child));
      }
    }
    this.#content = `${bufferBefore.join("\n")}${paste}${bufferAfter.join("\n")}`;
    this.#setContent();
    const newRange = new Range();
    let beforeLength = Math.sumPrecise(bufferBefore.map(line => line.length));
    for (const {
      firstChild
    } of this.editorDiv.childNodes) {
      if (firstChild.nodeType === Node.TEXT_NODE) {
        const length = firstChild.nodeValue.length;
        if (beforeLength <= length) {
          newRange.setStart(firstChild, beforeLength);
          newRange.setEnd(firstChild, beforeLength);
          break;
        }
        beforeLength -= length;
      }
    }
    selection.removeAllRanges();
    selection.addRange(newRange);
  }
  #setContent() {
    this.editorDiv.replaceChildren();
    if (!this.#content) {
      return;
    }
    for (const line of this.#content.split("\n")) {
      const div = document.createElement("div");
      div.append(line ? document.createTextNode(line) : document.createElement("br"));
      this.editorDiv.append(div);
    }
  }
  #serializeContent() {
    return this.#content.replaceAll("\xa0", " ");
  }
  static #deserializeContent(content) {
    return content.replaceAll(" ", "\xa0");
  }
  get contentDiv() {
    return this.editorDiv;
  }
  getPDFRect() {
    const padding = FreeTextEditor._internalPadding * this.parentScale;
    return this.getRect(padding, padding);
  }
  static async deserialize(data, parent, uiManager) {
    let initialData = null;
    if (data instanceof FreeTextAnnotationElement) {
      const {
        data: {
          defaultAppearanceData: {
            fontSize,
            fontColor
          },
          rect,
          rotation,
          id,
          popupRef,
          richText,
          contentsObj,
          creationDate,
          modificationDate
        },
        textContent,
        textPosition,
        parent: {
          page: {
            pageNumber
          }
        }
      } = data;
      if (!textContent?.length) {
        return null;
      }
      initialData = data = {
        annotationType: AnnotationEditorType.FREETEXT,
        color: Array.from(fontColor),
        fontSize,
        value: textContent.join("\n"),
        position: textPosition,
        pageIndex: pageNumber - 1,
        rect: rect.slice(0),
        rotation,
        annotationElementId: id,
        id,
        deleted: false,
        popupRef,
        comment: contentsObj?.str || null,
        richText,
        creationDate,
        modificationDate
      };
    }
    const editor = await super.deserialize(data, parent, uiManager);
    editor.#fontSize = data.fontSize;
    editor.color = Util.makeHexColor(...data.color);
    editor.#content = FreeTextEditor.#deserializeContent(data.value);
    editor._initialData = initialData;
    if (data.comment) {
      editor.setCommentData(data);
    }
    return editor;
  }
  serialize(isForCopying = false) {
    if (this.isEmpty()) {
      return null;
    }
    if (this.deleted) {
      return this.serializeDeleted();
    }
    const color = AnnotationEditor._colorManager.convert(this.isAttachedToDOM ? getComputedStyle(this.editorDiv).color : this.color);
    const serialized = Object.assign(super.serialize(isForCopying), {
      color,
      fontSize: this.#fontSize,
      value: this.#serializeContent()
    });
    this.addComment(serialized);
    if (isForCopying) {
      serialized.isCopy = true;
      return serialized;
    }
    if (this.annotationElementId && !this.#hasElementChanged(serialized)) {
      return null;
    }
    serialized.id = this.annotationElementId;
    return serialized;
  }
  #hasElementChanged(serialized) {
    const {
      value,
      fontSize,
      color,
      pageIndex
    } = this._initialData;
    return this.hasEditedComment || this._hasBeenMoved || serialized.value !== value || serialized.fontSize !== fontSize || serialized.color.some((c, i) => c !== color[i]) || serialized.pageIndex !== pageIndex;
  }
  renderAnnotationElement(annotation) {
    const content = super.renderAnnotationElement(annotation);
    if (!content) {
      return null;
    }
    const {
      style
    } = content;
    style.fontSize = `calc(${this.#fontSize}px * var(--total-scale-factor))`;
    style.color = this.color;
    content.replaceChildren();
    for (const line of this.#content.split("\n")) {
      const div = document.createElement("div");
      div.append(line ? document.createTextNode(line) : document.createElement("br"));
      content.append(div);
    }
    annotation.updateEdited({
      rect: this.getPDFRect(),
      popup: this._uiManager.hasCommentManager() || this.hasEditedComment ? this.comment : {
        text: this.#content
      }
    });
    return content;
  }
  resetAnnotationElement(annotation) {
    super.resetAnnotationElement(annotation);
    annotation.resetEdited();
  }
}

;// ./src/display/editor/draw.js




class DrawingOptions {
  #svgProperties = Object.create(null);
  updateProperty(name, value) {
    this[name] = value;
    this.updateSVGProperty(name, value);
  }
  updateProperties(properties) {
    if (!properties) {
      return;
    }
    for (const [name, value] of Object.entries(properties)) {
      if (!name.startsWith("_")) {
        this.updateProperty(name, value);
      }
    }
  }
  updateSVGProperty(name, value) {
    this.#svgProperties[name] = value;
  }
  toSVGProperties() {
    const root = this.#svgProperties;
    this.#svgProperties = Object.create(null);
    return {
      root
    };
  }
  reset() {
    this.#svgProperties = Object.create(null);
  }
  updateAll(options = this) {
    this.updateProperties(options);
  }
  clone() {
    unreachable("Not implemented");
  }
}
class DrawingEditor extends AnnotationEditor {
  #internalDiv = null;
  #mustBeCommitted;
  _clipPathId = null;
  _colorPicker = null;
  _drawId = null;
  _drawOutlines = null;
  _focusDrawId = null;
  static _currentDrawId = -1;
  static _currentParent = null;
  static #currentDraw = null;
  static #currentDrawingAC = null;
  static #currentDrawingOptions = null;
  static #currentClipPathId = null;
  static _INNER_MARGIN = 3;
  constructor(params) {
    super(params);
    this.#mustBeCommitted = params.mustBeCommitted || false;
    this._addOutlines(params);
  }
  onUpdatedColor() {
    this._colorPicker?.update(this.color);
    super.onUpdatedColor();
  }
  onUpdatedOpacity() {
    this._colorPicker?.updateOpacity?.(this.opacity);
  }
  _addOutlines(params) {
    if (params.drawOutlines) {
      this.#createDrawOutlines(params);
      this.#addToDrawLayer();
    }
  }
  #createDrawOutlines({
    drawOutlines,
    drawId,
    drawingOptions,
    clipPathId
  }) {
    this._drawOutlines = drawOutlines;
    this._drawingOptions ||= drawingOptions;
    if (!this.annotationElementId) {
      this._uiManager.a11yAlert(AnnotationEditor._l10nAlert[this.editorType]);
    }
    if (drawId >= 0) {
      this._drawId = drawId;
      this._clipPathId = clipPathId ?? null;
      this.parent.drawLayer.finalizeDraw(drawId, drawOutlines.defaultProperties);
      this.#createFocusOutline(this.parent);
    } else {
      this._drawId = this.#createDrawing(drawOutlines, this.parent);
    }
    this.#updateBbox(drawOutlines.box);
  }
  #createDrawing(drawOutlines, parent) {
    const {
      id,
      clipPathId
    } = parent.drawLayer.draw(DrawingEditor._mergeSVGProperties(this._drawingOptions.toSVGProperties(), drawOutlines.defaultSVGProperties), false, this.constructor._hasClipPath);
    if (this.constructor._hasClipPath) {
      this._clipPathId = clipPathId;
    }
    this.#createFocusOutline(parent);
    return id;
  }
  #createFocusOutline(parent) {
    const properties = this._drawOutlines.getFocusSVGProperties(this.#rotationAngle);
    if (properties) {
      this._focusDrawId = parent.drawLayer.drawOutline(properties, this._drawOutlines.focusMustRemoveSelfIntersections);
    }
  }
  #updateFocusOutline(angle = this.#rotationAngle) {
    if (this._focusDrawId === null) {
      return;
    }
    this.parent?.drawLayer.updateProperties(this._focusDrawId, this._drawOutlines.getFocusSVGProperties(angle));
  }
  #toggleFocusOutlineClass(rootClass) {
    if (this._focusDrawId !== null) {
      this.parent?.drawLayer.updateProperties(this._focusDrawId, {
        rootClass
      });
    }
  }
  #updateVisibility() {
    const {
      parent,
      _drawId,
      _focusDrawId,
      _isVisible
    } = this;
    if (!parent || _drawId === null) {
      return;
    }
    const rootClass = {
      hidden: !_isVisible
    };
    parent.drawLayer.updateProperties(_drawId, {
      rootClass
    });
    if (_focusDrawId !== null) {
      parent.drawLayer.updateProperties(_focusDrawId, {
        rootClass
      });
    }
  }
  static _mergeSVGProperties(p1, p2) {
    const p1Keys = new Set(Object.keys(p1));
    for (const [key, value] of Object.entries(p2)) {
      if (p1Keys.has(key)) {
        Object.assign(p1[key], value);
      } else {
        p1[key] = value;
      }
    }
    return p1;
  }
  static getDefaultDrawingOptions(_options) {
    unreachable("Not implemented");
  }
  static get typesMap() {
    unreachable("Not implemented");
  }
  static get isDrawer() {
    return true;
  }
  static get _hasClipPath() {
    return false;
  }
  static get _hasDrawClass() {
    return true;
  }
  static get supportMultipleDrawings() {
    return false;
  }
  get _drawRotation() {
    return this.rotation;
  }
  get _opacityName() {
    return this.constructor.typesMap.get(this.opacityType);
  }
  get #rotationAngle() {
    return (this.parentRotation - this._drawRotation + 360) % 360;
  }
  static updateDefaultParams(type, value) {
    const propertyName = this.typesMap.get(type);
    if (propertyName) {
      this._defaultDrawingOptions.updateProperty(propertyName, value);
    }
    if (this._currentParent) {
      DrawingEditor.#currentDraw.updateProperty(propertyName, value);
      this._currentParent.drawLayer.updateProperties(this._currentDrawId, this._defaultDrawingOptions.toSVGProperties());
    }
  }
  updateParams(type, value) {
    const propertyName = this.constructor.typesMap.get(type);
    if (propertyName) {
      this._updateProperty(type, propertyName, value);
    }
  }
  static get defaultPropertiesToUpdate() {
    const properties = [];
    const options = this._defaultDrawingOptions;
    for (const [type, name] of this.typesMap) {
      properties.push([type, options[name]]);
    }
    return properties;
  }
  get propertiesToUpdate() {
    const properties = [];
    const {
      _drawingOptions
    } = this;
    for (const [type, name] of this.constructor.typesMap) {
      properties.push([type, _drawingOptions[name]]);
    }
    return properties;
  }
  _updateProperty(type, name, value) {
    const options = this._drawingOptions;
    const savedValue = options[name];
    const setter = val => {
      options.updateProperty(name, val);
      const bbox = this._drawOutlines.updateProperty(name, val);
      if (bbox) {
        this.#updateBbox(bbox);
      }
      this.parent?.drawLayer.updateProperties(this._drawId, options.toSVGProperties());
      if (type === this.colorType) {
        this.onUpdatedColor();
      } else if (type === this.opacityType) {
        this.onUpdatedOpacity();
      }
    };
    this.addCommands({
      cmd: setter.bind(this, value),
      undo: setter.bind(this, savedValue),
      post: this._uiManager.updateUI.bind(this._uiManager, this),
      mustExec: true,
      type,
      overwriteIfSameType: true,
      keepUndo: true
    });
  }
  _updateColorAndOpacity(color, opacity, type = this.colorAndOpacityType) {
    const colorName = this.constructor.typesMap.get(this.colorType);
    const opacityName = this._opacityName;
    const options = this._drawingOptions;
    const savedColor = options[colorName];
    const savedOpacity = options[opacityName];
    const setter = (c, op) => {
      options.updateProperty(colorName, c);
      options.updateProperty(opacityName, op);
      this._drawOutlines.updateProperty(colorName, c);
      this._drawOutlines.updateProperty(opacityName, op);
      this.parent?.drawLayer.updateProperties(this._drawId, options.toSVGProperties());
      this.onUpdatedColor();
      this.onUpdatedOpacity();
    };
    this.addCommands({
      cmd: setter.bind(this, color, opacity),
      undo: setter.bind(this, savedColor, savedOpacity),
      post: this._uiManager.updateUI.bind(this._uiManager, this),
      mustExec: true,
      type,
      overwriteIfSameType: true,
      keepUndo: true
    });
  }
  _onResizing() {
    this.parent?.drawLayer.updateProperties(this._drawId, DrawingEditor._mergeSVGProperties(this._drawOutlines.getPathResizingSVGProperties(this.#convertToDrawSpace()), {
      bbox: this.#rotateBox()
    }));
  }
  _onResized() {
    this.parent?.drawLayer.updateProperties(this._drawId, DrawingEditor._mergeSVGProperties(this._drawOutlines.getPathResizedSVGProperties(this.#convertToDrawSpace()), {
      bbox: this.#rotateBox()
    }));
    this.#updateFocusOutline();
  }
  _onTranslating(_x, _y) {
    this.parent?.drawLayer.updateProperties(this._drawId, {
      bbox: this.#rotateBox()
    });
  }
  _onTranslated() {
    this.parent?.drawLayer.updateProperties(this._drawId, DrawingEditor._mergeSVGProperties(this._drawOutlines.getPathTranslatedSVGProperties(this.#convertToDrawSpace(), this.parentDimensions), {
      bbox: this.#rotateBox()
    }));
  }
  _onStartDragging() {
    this.parent?.drawLayer.updateProperties(this._drawId, {
      rootClass: {
        moving: true
      }
    });
  }
  _onStopDragging() {
    this.parent?.drawLayer.updateProperties(this._drawId, {
      rootClass: {
        moving: false
      }
    });
  }
  get _mustBeDisabledOnCommit() {
    return true;
  }
  commit() {
    super.commit();
    if (this._mustBeDisabledOnCommit) {
      this.disableEditMode();
      this.disableEditing();
    }
  }
  disableEditing() {
    super.disableEditing();
    this.div.classList.toggle("disabled", true);
  }
  enableEditing() {
    super.enableEditing();
    this.div.classList.toggle("disabled", false);
  }
  getBaseTranslation() {
    return [0, 0];
  }
  get isResizable() {
    return true;
  }
  onceAdded(focus) {
    if (!this.annotationElementId && this._drawId !== null) {
      this.parent.addUndoableEditor(this);
    }
    this._isDraggable = true;
    if (this.#mustBeCommitted) {
      this.#mustBeCommitted = false;
      this.commit();
      this.parent.setSelected(this);
      if (focus && this.isOnScreen) {
        this.div.focus();
      }
    }
  }
  remove() {
    this._uiManager.removeShouldRescale(this);
    this.#cleanDrawLayer();
    super.remove();
  }
  rebuild() {
    if (!this.parent) {
      return;
    }
    super.rebuild();
    if (this.div === null) {
      return;
    }
    this.#addToDrawLayer();
    this.#updateBbox(this._drawOutlines.box);
    if (!this.isAttachedToDOM) {
      this.parent.add(this);
    }
  }
  setParent(parent) {
    let mustBeSelected = false;
    if (this.parent && !parent) {
      this._uiManager.removeShouldRescale(this);
      this.#cleanDrawLayer();
    } else if (parent) {
      this._uiManager.addShouldRescale(this);
      this.#addToDrawLayer(parent);
      mustBeSelected = !this.parent && this.div?.classList.contains("selectedEditor");
    }
    super.setParent(parent);
    this.#updateVisibility();
    if (mustBeSelected) {
      this.select();
    }
  }
  #cleanDrawLayer() {
    if (this._drawId === null || !this.parent) {
      return;
    }
    const {
      drawLayer
    } = this.parent;
    drawLayer.remove(this._drawId);
    this._drawId = null;
    if (this._focusDrawId !== null) {
      drawLayer.remove(this._focusDrawId);
      this._focusDrawId = null;
    }
    this._drawingOptions.reset();
  }
  #addToDrawLayer(parent = this.parent) {
    if (this._drawId !== null && this.parent === parent) {
      return;
    }
    if (this._drawId !== null) {
      const {
        drawLayer
      } = this.parent;
      drawLayer.updateParent(this._drawId, parent.drawLayer);
      if (this._focusDrawId !== null) {
        drawLayer.updateParent(this._focusDrawId, parent.drawLayer);
      }
      return;
    }
    this._drawingOptions.updateAll();
    this._drawId = this.#createDrawing(this._drawOutlines, parent);
    if (this._clipPathId && this.#internalDiv) {
      this.#internalDiv.style.clipPath = this._clipPathId;
    }
  }
  #convertToParentSpace([x, y, width, height]) {
    const {
      parentDimensions: [pW, pH],
      _drawRotation: rotation
    } = this;
    switch (rotation) {
      case 90:
        return [y, 1 - x, width * (pH / pW), height * (pW / pH)];
      case 180:
        return [1 - x, 1 - y, width, height];
      case 270:
        return [1 - y, x, width * (pH / pW), height * (pW / pH)];
      default:
        return [x, y, width, height];
    }
  }
  #convertToDrawSpace() {
    const {
      x,
      y,
      width,
      height,
      parentDimensions: [pW, pH],
      _drawRotation: rotation
    } = this;
    switch (rotation) {
      case 90:
        return [1 - y, x, width * (pW / pH), height * (pH / pW)];
      case 180:
        return [1 - x, 1 - y, width, height];
      case 270:
        return [y, 1 - x, width * (pW / pH), height * (pH / pW)];
      default:
        return [x, y, width, height];
    }
  }
  #updateBbox(bbox) {
    [this.x, this.y, this.width, this.height] = this.#convertToParentSpace(bbox);
    if (this.div) {
      this.fixAndSetPosition();
      this.setDims();
    }
    this._onResized();
  }
  #rotateBox(parentRotation = this.parentRotation) {
    const {
      x,
      y,
      width,
      height,
      _drawRotation: rotation,
      parentDimensions: [pW, pH]
    } = this;
    switch ((rotation * 4 + parentRotation) / 90) {
      case 1:
        return [1 - y - height, x, height, width];
      case 2:
        return [1 - x - width, 1 - y - height, width, height];
      case 3:
        return [y, 1 - x - width, height, width];
      case 4:
        return [x, y - width * (pW / pH), height * (pH / pW), width * (pW / pH)];
      case 5:
        return [1 - y, x, width * (pW / pH), height * (pH / pW)];
      case 6:
        return [1 - x - height * (pH / pW), 1 - y, height * (pH / pW), width * (pW / pH)];
      case 7:
        return [y - width * (pW / pH), 1 - x - height * (pH / pW), width * (pW / pH), height * (pH / pW)];
      case 8:
        return [x - width, y - height, width, height];
      case 9:
        return [1 - y, x - width, height, width];
      case 10:
        return [1 - x, 1 - y, width, height];
      case 11:
        return [y - height, 1 - x, height, width];
      case 12:
        return [x - height * (pH / pW), y, height * (pH / pW), width * (pW / pH)];
      case 13:
        return [1 - y - width * (pW / pH), x - height * (pH / pW), width * (pW / pH), height * (pH / pW)];
      case 14:
        return [1 - x, 1 - y - width * (pW / pH), height * (pH / pW), width * (pW / pH)];
      case 15:
        return [y, 1 - x, width * (pW / pH), height * (pH / pW)];
      default:
        return [x, y, width, height];
    }
  }
  rotate(parentRotation = this.parentRotation) {
    if (!this.parent || this._drawId === null) {
      return;
    }
    const angle = (parentRotation - this._drawRotation + 360) % 360;
    this.parent.drawLayer.updateProperties(this._drawId, DrawingEditor._mergeSVGProperties({
      bbox: this.#rotateBox(parentRotation)
    }, this._drawOutlines.updateRotation(angle)));
    this.#updateFocusOutline(angle);
  }
  show(visible = this._isVisible) {
    super.show(visible);
    this.#updateVisibility();
  }
  select() {
    super.select();
    this.#toggleFocusOutlineClass({
      hovered: false,
      selected: true
    });
  }
  unselect() {
    super.unselect();
    this.#toggleFocusOutlineClass({
      selected: false
    });
  }
  pointerover() {
    if (!this.isSelected) {
      this.#toggleFocusOutlineClass({
        hovered: true
      });
    }
  }
  pointerleave() {
    if (!this.isSelected) {
      this.#toggleFocusOutlineClass({
        hovered: false
      });
    }
  }
  onScaleChanging() {
    if (!this.parent) {
      return;
    }
    const bbox = this._drawOutlines.updateParentDimensions(this.parentDimensions, this.parent.scale);
    if (bbox) {
      this.#updateBbox(bbox);
    }
  }
  static onScaleChangingWhenDrawing() {}
  render() {
    if (this.div) {
      return this.div;
    }
    let baseX, baseY;
    if (this._isCopy) {
      baseX = this.x;
      baseY = this.y;
    }
    const div = super.render();
    if (this.constructor._hasDrawClass) {
      div.classList.add("draw");
    }
    const drawDiv = this.#internalDiv = document.createElement("div");
    div.append(drawDiv);
    drawDiv.setAttribute("aria-hidden", "true");
    drawDiv.className = "internal";
    if (this._clipPathId) {
      drawDiv.style.clipPath = this._clipPathId;
    }
    bindEvents(this, drawDiv, ["pointerover", "pointerleave"]);
    this.setDims();
    this._uiManager.addShouldRescale(this);
    this.disableEditing();
    if (this._isCopy) {
      this._moveAfterPaste(baseX, baseY);
    }
    return div;
  }
  static createDrawerInstance(_params) {
    unreachable("Not implemented");
  }
  static _getDrawingTarget(_parent, {
    target
  }) {
    return target;
  }
  static _getPointerCoords({
    offsetX,
    offsetY,
    clientX,
    clientY
  }, referenceEvent = null) {
    if (!referenceEvent) {
      return [offsetX, offsetY];
    }
    let deltaX = clientX - referenceEvent.clientX;
    let deltaY = clientY - referenceEvent.clientY;
    switch (this._currentParent.viewport.rotation) {
      case 90:
        [deltaX, deltaY] = [deltaY, -deltaX];
        break;
      case 180:
        [deltaX, deltaY] = [-deltaX, -deltaY];
        break;
      case 270:
        [deltaX, deltaY] = [-deltaY, deltaX];
        break;
    }
    return [referenceEvent.offsetX + deltaX, referenceEvent.offsetY + deltaY];
  }
  static _addDrawingListeners(_target, _signal) {}
  static _endDrawingSession(isAborted = false) {
    return this._currentParent.endDrawingSession(isAborted);
  }
  static startDrawing(parent, uiManager, isLTR, event) {
    const {
      pointerId,
      pointerType
    } = event;
    if (CurrentPointers.isInitializedAndDifferentPointerType(pointerType)) {
      return;
    }
    const target = this._getDrawingTarget(parent, event);
    const [x, y] = this._getPointerCoords(event);
    const {
      viewport: {
        rotation
      }
    } = parent;
    const {
      x: boxX,
      y: boxY,
      width: parentWidth,
      height: parentHeight
    } = target.getBoundingClientRect();
    const ac = DrawingEditor.#currentDrawingAC = new AbortController();
    const signal = parent.combinedSignal(ac);
    CurrentPointers.setPointer(pointerType, pointerId);
    window.addEventListener("pointerup", e => {
      if (CurrentPointers.isSamePointerIdOrRemove(e.pointerId)) {
        this._endDraw(e);
      }
    }, {
      signal
    });
    window.addEventListener("pointercancel", e => {
      if (CurrentPointers.isSamePointerIdOrRemove(e.pointerId)) {
        this._endDrawingSession();
      }
    }, {
      signal
    });
    window.addEventListener("pointerdown", e => {
      if (!CurrentPointers.isSamePointerType(e.pointerType)) {
        return;
      }
      CurrentPointers.initializeAndAddPointerId(e.pointerId);
      if (DrawingEditor.#currentDraw.isCancellable()) {
        DrawingEditor.#currentDraw.removeLastElement();
        if (DrawingEditor.#currentDraw.isEmpty()) {
          this._endDrawingSession(true);
        } else {
          this._endDraw(null);
        }
      }
    }, {
      capture: true,
      passive: false,
      signal
    });
    window.addEventListener("contextmenu", noContextMenu, {
      signal
    });
    target.addEventListener("pointermove", this._drawMove.bind(this), {
      signal
    });
    target.addEventListener("touchmove", e => {
      if (CurrentPointers.isSameTimeStamp(e.timeStamp)) {
        stopEvent(e);
      }
    }, {
      signal
    });
    this._addDrawingListeners(target, signal);
    parent.toggleDrawing();
    uiManager._editorUndoBar?.hide();
    if (DrawingEditor.#currentDraw) {
      parent.drawLayer.updateProperties(this._currentDrawId, DrawingEditor.#currentDraw.startNew(x, y, parentWidth, parentHeight, rotation, event.timeStamp));
      return;
    }
    uiManager.updateUIForDefaultProperties(this);
    DrawingEditor.#currentDraw = this.createDrawerInstance({
      x,
      y,
      box: [boxX, boxY, parentWidth, parentHeight],
      rotation,
      parent,
      isLTR,
      timeStamp: event.timeStamp
    });
    DrawingEditor.#currentDrawingOptions = this.getDefaultDrawingOptions();
    this._currentParent = parent;
    const {
      id,
      clipPathId
    } = parent.drawLayer.draw(this._mergeSVGProperties(DrawingEditor.#currentDrawingOptions.toSVGProperties(), DrawingEditor.#currentDraw.defaultSVGProperties), true, this._hasClipPath);
    this._currentDrawId = id;
    DrawingEditor.#currentClipPathId = this._hasClipPath ? clipPathId : null;
  }
  static _drawMove(event) {
    CurrentPointers.isSameTimeStamp(event.timeStamp);
    if (!DrawingEditor.#currentDraw || !CurrentPointers.isSamePointerId(event.pointerId)) {
      return;
    }
    if (CurrentPointers.isUsingMultiplePointers()) {
      this._endDraw(event);
      return;
    }
    let properties;
    const coalesced = event.getCoalescedEvents?.();
    if (coalesced?.length) {
      const points = [];
      const timeStamps = [];
      for (const sample of coalesced) {
        points.push(...this._getPointerCoords(sample, event));
        timeStamps.push(sample.timeStamp);
      }
      properties = DrawingEditor.#currentDraw.addPoints(points, timeStamps);
    } else {
      properties = DrawingEditor.#currentDraw.add(...this._getPointerCoords(event), event.timeStamp);
    }
    this._currentParent.drawLayer.updateProperties(this._currentDrawId, properties);
    CurrentPointers.setTimeStamp(event.timeStamp);
    stopEvent(event);
  }
  static _cleanup(all) {
    if (all) {
      this._currentDrawId = -1;
      this._currentParent = null;
      DrawingEditor.#currentDraw = null;
      DrawingEditor.#currentDrawingOptions = null;
      DrawingEditor.#currentClipPathId = null;
      CurrentPointers.clearTimeStamp();
    }
    if (DrawingEditor.#currentDrawingAC) {
      DrawingEditor.#currentDrawingAC.abort();
      DrawingEditor.#currentDrawingAC = null;
      CurrentPointers.clearPointerIds();
    }
  }
  static _endDraw(event) {
    const parent = this._currentParent;
    if (!parent) {
      return;
    }
    parent.toggleDrawing(true);
    this._cleanup(false);
    parent.drawLayer.updateProperties(this._currentDrawId, event?.target === parent.div ? DrawingEditor.#currentDraw.end(...this._getPointerCoords(event), event.timeStamp) : DrawingEditor.#currentDraw.end());
    if (this.supportMultipleDrawings) {
      const draw = DrawingEditor.#currentDraw;
      const drawId = this._currentDrawId;
      const lastElement = draw.getLastElement();
      parent.addCommands({
        cmd: () => {
          parent.drawLayer.updateProperties(drawId, draw.setLastElement(lastElement));
        },
        undo: () => {
          parent.drawLayer.updateProperties(drawId, draw.removeLastElement());
        },
        mustExec: false,
        type: AnnotationEditorParamsType.DRAW_STEP
      });
      return;
    }
    this.endDrawing(false);
  }
  static endDrawing(isAborted) {
    const parent = this._currentParent;
    if (!parent) {
      return null;
    }
    parent.toggleDrawing(true);
    parent.cleanUndoStack(AnnotationEditorParamsType.DRAW_STEP);
    if (!DrawingEditor.#currentDraw.isEmpty()) {
      const {
        pageDimensions: [pageWidth, pageHeight],
        scale
      } = parent;
      const editor = parent.createAndAddNewEditor({
        offsetX: 0,
        offsetY: 0
      }, false, {
        drawId: this._currentDrawId,
        clipPathId: DrawingEditor.#currentClipPathId,
        drawOutlines: DrawingEditor.#currentDraw.getOutlines(pageWidth * scale, pageHeight * scale, scale, this._INNER_MARGIN),
        drawingOptions: DrawingEditor.#currentDrawingOptions,
        mustBeCommitted: !isAborted
      });
      this._cleanup(true);
      return editor;
    }
    parent.drawLayer.remove(this._currentDrawId);
    this._cleanup(true);
    return null;
  }
  createDrawingOptions(_data) {}
  static deserializeDraw(_pageX, _pageY, _pageWidth, _pageHeight, _innerMargin, _data, _uiManager) {
    unreachable("Not implemented");
  }
  static async deserialize(data, parent, uiManager) {
    const {
      rawDims: {
        pageWidth,
        pageHeight,
        pageX,
        pageY
      }
    } = parent.viewport;
    const drawOutlines = this.deserializeDraw(pageX, pageY, pageWidth, pageHeight, this._INNER_MARGIN, data, uiManager);
    const editor = await super.deserialize(data, parent, uiManager);
    editor.createDrawingOptions(data);
    editor.#createDrawOutlines({
      drawOutlines
    });
    editor.#addToDrawLayer();
    editor.onScaleChanging();
    editor.rotate();
    return editor;
  }
  serializeDraw(isForCopying) {
    const [pageX, pageY] = this.pageTranslation;
    const [pageWidth, pageHeight] = this.pageDimensions;
    return this._drawOutlines.serialize([pageX, pageY, pageWidth, pageHeight], isForCopying);
  }
  renderAnnotationElement(annotation) {
    annotation.updateEdited({
      rect: this.getPDFRect()
    });
    return null;
  }
  static canCreateNewEmptyEditor() {
    return false;
  }
}

;// ./src/display/editor/drawers/outline.js

class Outline {
  static PRECISION = 1e-4;
  focusOutline = null;
  toSVGPath() {
    unreachable("Abstract method `toSVGPath` must be implemented.");
  }
  get box() {
    unreachable("Abstract getter `box` must be implemented.");
  }
  serialize(_bbox, _rotation) {
    unreachable("Abstract method `serialize` must be implemented.");
  }
  get defaultSVGProperties() {
    unreachable("Abstract getter `defaultSVGProperties` must be implemented.");
  }
  get defaultProperties() {
    return this.defaultSVGProperties;
  }
  getFocusSVGProperties(_rotation) {
    return null;
  }
  get focusMustRemoveSelfIntersections() {
    return false;
  }
  updateProperty(_name, _value) {
    return null;
  }
  updateParentDimensions(_dimensions, _scale) {
    return null;
  }
  serializeQuadPoints(_pageTranslation, _pageDimensions) {
    return null;
  }
  updateRotation(_rotation) {
    return {};
  }
  getPathResizingSVGProperties(_bbox) {
    return {};
  }
  getPathResizedSVGProperties(_bbox) {
    return {};
  }
  getPathTranslatedSVGProperties(_bbox, _parentDimensions) {
    return {};
  }
  static _rotateBox([x, y, width, height], angle) {
    switch (angle) {
      case 90:
        return [1 - y - height, x, height, width];
      case 180:
        return [1 - x - width, 1 - y - height, width, height];
      case 270:
        return [y, 1 - x - width, height, width];
    }
    return [x, y, width, height];
  }
  static _rescale(src, tx, ty, sx, sy, dest) {
    dest ||= new Float32Array(src.length);
    for (let i = 0, ii = src.length; i < ii; i += 2) {
      dest[i] = tx + src[i] * sx;
      dest[i + 1] = ty + src[i + 1] * sy;
    }
    return dest;
  }
  static _rescaleAndSwap(src, tx, ty, sx, sy, dest) {
    dest ||= new Float32Array(src.length);
    for (let i = 0, ii = src.length; i < ii; i += 2) {
      dest[i] = tx + src[i + 1] * sx;
      dest[i + 1] = ty + src[i] * sy;
    }
    return dest;
  }
  static _translate(src, tx, ty, dest) {
    dest ||= new Float32Array(src.length);
    for (let i = 0, ii = src.length; i < ii; i += 2) {
      dest[i] = tx + src[i];
      dest[i + 1] = ty + src[i + 1];
    }
    return dest;
  }
  static svgRound(x) {
    return Math.round(x * 10000);
  }
  static _normalizePoint(x, y, parentWidth, parentHeight, rotation, dest = []) {
    switch (rotation) {
      case 90:
        dest[0] = 1 - y / parentWidth;
        dest[1] = x / parentHeight;
        break;
      case 180:
        dest[0] = 1 - x / parentWidth;
        dest[1] = 1 - y / parentHeight;
        break;
      case 270:
        dest[0] = y / parentWidth;
        dest[1] = 1 - x / parentHeight;
        break;
      default:
        dest[0] = x / parentWidth;
        dest[1] = y / parentHeight;
        break;
    }
    return dest;
  }
  static createBezierPoints(x1, y1, x2, y2, x3, y3, dest = []) {
    dest.push((x1 + 5 * x2) / 6, (y1 + 5 * y2) / 6, (5 * x2 + x3) / 6, (5 * y2 + y3) / 6, (x2 + x3) / 2, (y2 + y3) / 2);
    return dest;
  }
}

;// ./src/display/editor/drawers/freedraw.js


class FreeDrawOutliner {
  #box;
  #bottom = [];
  #innerMargin;
  #isLTR;
  #top = [];
  #last = new Float32Array(18);
  #lastX;
  #lastY;
  #min;
  #min_dist;
  #scaleFactor;
  #thickness;
  #points = [];
  static #MIN_DIST = 8;
  static #MIN_DIFF = 2;
  static #MIN = FreeDrawOutliner.#MIN_DIST + FreeDrawOutliner.#MIN_DIFF;
  constructor(x, y, box, scaleFactor, thickness, isLTR, innerMargin = 0) {
    this.#box = box;
    this.#thickness = thickness * scaleFactor;
    this.#isLTR = isLTR;
    this.#last.set([NaN, NaN, NaN, NaN, x, y], 6);
    this.#innerMargin = innerMargin;
    this.#min_dist = FreeDrawOutliner.#MIN_DIST * scaleFactor;
    this.#min = FreeDrawOutliner.#MIN * scaleFactor;
    this.#scaleFactor = scaleFactor;
    this.#points.push(x, y);
  }
  isEmpty() {
    return isNaN(this.#last[8]);
  }
  isCancellable() {
    return this.#points.length <= 10;
  }
  removeLastElement() {
    this.#last.fill(NaN);
    this.#top.length = this.#bottom.length = this.#points.length = 0;
    return {
      path: {
        d: ""
      }
    };
  }
  #getLastCoords() {
    const lastTop = this.#last.subarray(4, 6);
    const lastBottom = this.#last.subarray(16, 18);
    const [x, y, width, height] = this.#box;
    return [(this.#lastX + (lastTop[0] - lastBottom[0]) / 2 - x) / width, (this.#lastY + (lastTop[1] - lastBottom[1]) / 2 - y) / height, (this.#lastX + (lastBottom[0] - lastTop[0]) / 2 - x) / width, (this.#lastY + (lastBottom[1] - lastTop[1]) / 2 - y) / height];
  }
  add(x, y) {
    this.#lastX = x;
    this.#lastY = y;
    const [layerX, layerY, layerWidth, layerHeight] = this.#box;
    let [x1, y1, x2, y2] = this.#last.subarray(8, 12);
    const diffX = x - x2;
    const diffY = y - y2;
    const d = Math.hypot(diffX, diffY);
    if (d < this.#min) {
      return false;
    }
    const diffD = d - this.#min_dist;
    const K = diffD / d;
    const shiftX = K * diffX;
    const shiftY = K * diffY;
    let x0 = x1;
    let y0 = y1;
    x1 = x2;
    y1 = y2;
    x2 += shiftX;
    y2 += shiftY;
    this.#points?.push(x, y);
    const nX = -shiftY / diffD;
    const nY = shiftX / diffD;
    const thX = nX * this.#thickness;
    const thY = nY * this.#thickness;
    this.#last.set(this.#last.subarray(2, 8), 0);
    this.#last.set([x2 + thX, y2 + thY], 4);
    this.#last.set(this.#last.subarray(14, 18), 12);
    this.#last.set([x2 - thX, y2 - thY], 16);
    if (isNaN(this.#last[6])) {
      if (this.#top.length === 0) {
        this.#last.set([x1 + thX, y1 + thY], 2);
        this.#top.push(NaN, NaN, NaN, NaN, (x1 + thX - layerX) / layerWidth, (y1 + thY - layerY) / layerHeight);
        this.#last.set([x1 - thX, y1 - thY], 14);
        this.#bottom.push(NaN, NaN, NaN, NaN, (x1 - thX - layerX) / layerWidth, (y1 - thY - layerY) / layerHeight);
      }
      this.#last.set([x0, y0, x1, y1, x2, y2], 6);
      return !this.isEmpty();
    }
    this.#last.set([x0, y0, x1, y1, x2, y2], 6);
    const angle = Math.abs(Math.atan2(y0 - y1, x0 - x1) - Math.atan2(shiftY, shiftX));
    if (angle < Math.PI / 2) {
      [x1, y1, x2, y2] = this.#last.subarray(2, 6);
      this.#top.push(NaN, NaN, NaN, NaN, ((x1 + x2) / 2 - layerX) / layerWidth, ((y1 + y2) / 2 - layerY) / layerHeight);
      [x1, y1, x0, y0] = this.#last.subarray(14, 18);
      this.#bottom.push(NaN, NaN, NaN, NaN, ((x0 + x1) / 2 - layerX) / layerWidth, ((y0 + y1) / 2 - layerY) / layerHeight);
      return true;
    }
    [x0, y0, x1, y1, x2, y2] = this.#last.subarray(0, 6);
    this.#top.push(((x0 + 5 * x1) / 6 - layerX) / layerWidth, ((y0 + 5 * y1) / 6 - layerY) / layerHeight, ((5 * x1 + x2) / 6 - layerX) / layerWidth, ((5 * y1 + y2) / 6 - layerY) / layerHeight, ((x1 + x2) / 2 - layerX) / layerWidth, ((y1 + y2) / 2 - layerY) / layerHeight);
    [x2, y2, x1, y1, x0, y0] = this.#last.subarray(12, 18);
    this.#bottom.push(((x0 + 5 * x1) / 6 - layerX) / layerWidth, ((y0 + 5 * y1) / 6 - layerY) / layerHeight, ((5 * x1 + x2) / 6 - layerX) / layerWidth, ((5 * y1 + y2) / 6 - layerY) / layerHeight, ((x1 + x2) / 2 - layerX) / layerWidth, ((y1 + y2) / 2 - layerY) / layerHeight);
    return true;
  }
  toSVGPath() {
    if (this.isEmpty()) {
      return "";
    }
    const top = this.#top;
    const bottom = this.#bottom;
    if (isNaN(this.#last[6]) && !this.isEmpty()) {
      return this.#toSVGPathTwoPoints();
    }
    const buffer = [];
    buffer.push(`M${top[4]} ${top[5]}`);
    for (let i = 6; i < top.length; i += 6) {
      if (isNaN(top[i])) {
        buffer.push(`L${top[i + 4]} ${top[i + 5]}`);
      } else {
        buffer.push(`C${top[i]} ${top[i + 1]} ${top[i + 2]} ${top[i + 3]} ${top[i + 4]} ${top[i + 5]}`);
      }
    }
    this.#toSVGPathEnd(buffer);
    for (let i = bottom.length - 6; i >= 6; i -= 6) {
      if (isNaN(bottom[i])) {
        buffer.push(`L${bottom[i + 4]} ${bottom[i + 5]}`);
      } else {
        buffer.push(`C${bottom[i]} ${bottom[i + 1]} ${bottom[i + 2]} ${bottom[i + 3]} ${bottom[i + 4]} ${bottom[i + 5]}`);
      }
    }
    this.#toSVGPathStart(buffer);
    return buffer.join(" ");
  }
  #toSVGPathTwoPoints() {
    const [x, y, width, height] = this.#box;
    const [lastTopX, lastTopY, lastBottomX, lastBottomY] = this.#getLastCoords();
    return `M${(this.#last[2] - x) / width} ${(this.#last[3] - y) / height} L${(this.#last[4] - x) / width} ${(this.#last[5] - y) / height} L${lastTopX} ${lastTopY} L${lastBottomX} ${lastBottomY} L${(this.#last[16] - x) / width} ${(this.#last[17] - y) / height} L${(this.#last[14] - x) / width} ${(this.#last[15] - y) / height} Z`;
  }
  #toSVGPathStart(buffer) {
    const bottom = this.#bottom;
    buffer.push(`L${bottom[4]} ${bottom[5]} Z`);
  }
  #toSVGPathEnd(buffer) {
    const [x, y, width, height] = this.#box;
    const lastTop = this.#last.subarray(4, 6);
    const lastBottom = this.#last.subarray(16, 18);
    const [lastTopX, lastTopY, lastBottomX, lastBottomY] = this.#getLastCoords();
    buffer.push(`L${(lastTop[0] - x) / width} ${(lastTop[1] - y) / height} L${lastTopX} ${lastTopY} L${lastBottomX} ${lastBottomY} L${(lastBottom[0] - x) / width} ${(lastBottom[1] - y) / height}`);
  }
  newFreeDrawOutline(outline, points, box, scaleFactor, innerMargin, isLTR) {
    return new FreeDrawOutline(outline, points, box, scaleFactor, innerMargin, isLTR);
  }
  getOutlines() {
    const top = this.#top;
    const bottom = this.#bottom;
    const last = this.#last;
    const [layerX, layerY, layerWidth, layerHeight] = this.#box;
    const points = new Float32Array((this.#points?.length ?? 0) + 2);
    for (let i = 0, ii = points.length - 2; i < ii; i += 2) {
      points[i] = (this.#points[i] - layerX) / layerWidth;
      points[i + 1] = (this.#points[i + 1] - layerY) / layerHeight;
    }
    points[points.length - 2] = (this.#lastX - layerX) / layerWidth;
    points[points.length - 1] = (this.#lastY - layerY) / layerHeight;
    if (isNaN(last[6]) && !this.isEmpty()) {
      return this.#getOutlineTwoPoints(points);
    }
    const outline = new Float32Array(this.#top.length + 24 + this.#bottom.length);
    let N = top.length;
    for (let i = 0; i < N; i += 2) {
      if (isNaN(top[i])) {
        outline[i] = outline[i + 1] = NaN;
        continue;
      }
      outline[i] = top[i];
      outline[i + 1] = top[i + 1];
    }
    N = this.#getOutlineEnd(outline, N);
    for (let i = bottom.length - 6; i >= 6; i -= 6) {
      for (let j = 0; j < 6; j += 2) {
        if (isNaN(bottom[i + j])) {
          outline[N] = outline[N + 1] = NaN;
          N += 2;
          continue;
        }
        outline[N] = bottom[i + j];
        outline[N + 1] = bottom[i + j + 1];
        N += 2;
      }
    }
    this.#getOutlineStart(outline, N);
    return this.newFreeDrawOutline(outline, points, this.#box, this.#scaleFactor, this.#innerMargin, this.#isLTR);
  }
  #getOutlineTwoPoints(points) {
    const last = this.#last;
    const [layerX, layerY, layerWidth, layerHeight] = this.#box;
    const [lastTopX, lastTopY, lastBottomX, lastBottomY] = this.#getLastCoords();
    const outline = new Float32Array(36);
    outline.set([NaN, NaN, NaN, NaN, (last[2] - layerX) / layerWidth, (last[3] - layerY) / layerHeight, NaN, NaN, NaN, NaN, (last[4] - layerX) / layerWidth, (last[5] - layerY) / layerHeight, NaN, NaN, NaN, NaN, lastTopX, lastTopY, NaN, NaN, NaN, NaN, lastBottomX, lastBottomY, NaN, NaN, NaN, NaN, (last[16] - layerX) / layerWidth, (last[17] - layerY) / layerHeight, NaN, NaN, NaN, NaN, (last[14] - layerX) / layerWidth, (last[15] - layerY) / layerHeight], 0);
    return this.newFreeDrawOutline(outline, points, this.#box, this.#scaleFactor, this.#innerMargin, this.#isLTR);
  }
  #getOutlineStart(outline, pos) {
    const bottom = this.#bottom;
    outline.set([NaN, NaN, NaN, NaN, bottom[4], bottom[5]], pos);
    return pos += 6;
  }
  #getOutlineEnd(outline, pos) {
    const lastTop = this.#last.subarray(4, 6);
    const lastBottom = this.#last.subarray(16, 18);
    const [layerX, layerY, layerWidth, layerHeight] = this.#box;
    const [lastTopX, lastTopY, lastBottomX, lastBottomY] = this.#getLastCoords();
    outline.set([NaN, NaN, NaN, NaN, (lastTop[0] - layerX) / layerWidth, (lastTop[1] - layerY) / layerHeight, NaN, NaN, NaN, NaN, lastTopX, lastTopY, NaN, NaN, NaN, NaN, lastBottomX, lastBottomY, NaN, NaN, NaN, NaN, (lastBottom[0] - layerX) / layerWidth, (lastBottom[1] - layerY) / layerHeight], pos);
    return pos += 24;
  }
}
class FreeDrawOutline extends Outline {
  #box;
  #bbox = new Float32Array(4);
  #innerMargin;
  #isLTR;
  #points;
  #scaleFactor;
  #outline;
  constructor(outline, points, box, scaleFactor, innerMargin, isLTR) {
    super();
    this.#outline = outline;
    this.#points = points;
    this.#box = box;
    this.#scaleFactor = scaleFactor;
    this.#innerMargin = innerMargin;
    this.#isLTR = isLTR;
    this.firstPoint = [NaN, NaN];
    this.lastPoint = [NaN, NaN];
    this.#computeMinMax(isLTR);
    const [x, y, width, height] = this.#bbox;
    for (let i = 0, ii = outline.length; i < ii; i += 2) {
      outline[i] = (outline[i] - x) / width;
      outline[i + 1] = (outline[i + 1] - y) / height;
    }
    for (let i = 0, ii = points.length; i < ii; i += 2) {
      points[i] = (points[i] - x) / width;
      points[i + 1] = (points[i + 1] - y) / height;
    }
  }
  toSVGPath() {
    const buffer = [`M${this.#outline[4]} ${this.#outline[5]}`];
    for (let i = 6, ii = this.#outline.length; i < ii; i += 6) {
      if (isNaN(this.#outline[i])) {
        buffer.push(`L${this.#outline[i + 4]} ${this.#outline[i + 5]}`);
        continue;
      }
      buffer.push(`C${this.#outline[i]} ${this.#outline[i + 1]} ${this.#outline[i + 2]} ${this.#outline[i + 3]} ${this.#outline[i + 4]} ${this.#outline[i + 5]}`);
    }
    buffer.push("Z");
    return buffer.join(" ");
  }
  serialize([blX, blY, trX, trY], rotation) {
    const width = trX - blX;
    const height = trY - blY;
    let outline;
    let points;
    switch (rotation) {
      case 0:
        outline = Outline._rescale(this.#outline, blX, trY, width, -height);
        points = Outline._rescale(this.#points, blX, trY, width, -height);
        break;
      case 90:
        outline = Outline._rescaleAndSwap(this.#outline, blX, blY, width, height);
        points = Outline._rescaleAndSwap(this.#points, blX, blY, width, height);
        break;
      case 180:
        outline = Outline._rescale(this.#outline, trX, blY, -width, height);
        points = Outline._rescale(this.#points, trX, blY, -width, height);
        break;
      case 270:
        outline = Outline._rescaleAndSwap(this.#outline, trX, trY, -width, -height);
        points = Outline._rescaleAndSwap(this.#points, trX, trY, -width, -height);
        break;
    }
    return {
      outline: Array.from(outline),
      points: [Array.from(points)]
    };
  }
  #computeMinMax(isLTR) {
    const outline = this.#outline;
    let lastX = outline[4];
    let lastY = outline[5];
    const minMax = [lastX, lastY, lastX, lastY];
    let firstPointX = lastX;
    let firstPointY = lastY;
    let lastPointX = lastX;
    let lastPointY = lastY;
    const ltrCallback = isLTR ? Math.max : Math.min;
    const bezierBbox = new Float32Array(4);
    for (let i = 6, ii = outline.length; i < ii; i += 6) {
      const x = outline[i + 4],
        y = outline[i + 5];
      if (isNaN(outline[i])) {
        Util.pointBoundingBox(x, y, minMax);
        if (firstPointY > y) {
          firstPointX = x;
          firstPointY = y;
        } else if (firstPointY === y) {
          firstPointX = ltrCallback(firstPointX, x);
        }
        if (lastPointY < y) {
          lastPointX = x;
          lastPointY = y;
        } else if (lastPointY === y) {
          lastPointX = ltrCallback(lastPointX, x);
        }
      } else {
        bezierBbox.set(BBOX_INIT, 0);
        Util.bezierBoundingBox(lastX, lastY, ...outline.slice(i, i + 6), bezierBbox);
        Util.rectBoundingBox(...bezierBbox, minMax);
        if (firstPointY > bezierBbox[1]) {
          firstPointX = bezierBbox[0];
          firstPointY = bezierBbox[1];
        } else if (firstPointY === bezierBbox[1]) {
          firstPointX = ltrCallback(firstPointX, bezierBbox[0]);
        }
        if (lastPointY < bezierBbox[3]) {
          lastPointX = bezierBbox[2];
          lastPointY = bezierBbox[3];
        } else if (lastPointY === bezierBbox[3]) {
          lastPointX = ltrCallback(lastPointX, bezierBbox[2]);
        }
      }
      lastX = x;
      lastY = y;
    }
    const bbox = this.#bbox;
    bbox[0] = minMax[0] - this.#innerMargin;
    bbox[1] = minMax[1] - this.#innerMargin;
    bbox[2] = minMax[2] - minMax[0] + 2 * this.#innerMargin;
    bbox[3] = minMax[3] - minMax[1] + 2 * this.#innerMargin;
    this.firstPoint = [firstPointX, firstPointY];
    this.lastPoint = [lastPointX, lastPointY];
  }
  get box() {
    return this.#bbox;
  }
  newOutliner(x, y, box, scaleFactor, thickness, isLTR, innerMargin = 0) {
    return new FreeDrawOutliner(x, y, box, scaleFactor, thickness, isLTR, innerMargin);
  }
  updateThickness(thickness) {
    const outline = this.getNewOutline(thickness);
    this.#outline = outline.#outline;
    this.#points = outline.#points;
    this.#bbox.set(outline.#bbox);
    this.firstPoint = outline.firstPoint;
    this.lastPoint = outline.lastPoint;
    return this.#bbox;
  }
  getNewOutline(thickness, innerMargin) {
    const [x, y, width, height] = this.#bbox;
    const [layerX, layerY, layerWidth, layerHeight] = this.#box;
    const sx = width * layerWidth;
    const sy = height * layerHeight;
    const tx = x * layerWidth + layerX;
    const ty = y * layerHeight + layerY;
    const points = this.#points;
    const outliner = this.newOutliner(points[0] * sx + tx, points[1] * sy + ty, this.#box, this.#scaleFactor, thickness, this.#isLTR, innerMargin ?? this.#innerMargin);
    for (let i = 2, ii = points.length; i < ii; i += 2) {
      outliner.add(points[i] * sx + tx, points[i + 1] * sy + ty);
    }
    return outliner.getOutlines();
  }
}

;// ./src/display/editor/drawers/highlight.js



function getHighlightSVGProperties(outline) {
  return {
    bbox: outline.box,
    root: {
      viewBox: "0 0 1 1"
    },
    rootClass: {
      highlight: true,
      free: outline.isFree
    },
    path: {
      d: outline.toSVGPath()
    }
  };
}
function getHighlightFocusSVGProperties(outline, rotation) {
  const {
    focusOutline
  } = outline;
  return {
    bbox: Outline._rotateBox(focusOutline.box, rotation),
    root: {
      "data-main-rotation": rotation
    },
    rootClass: {
      highlightOutline: true,
      free: outline.isFree
    },
    path: {
      d: focusOutline.toSVGPath()
    }
  };
}
class HighlightOutliner {
  #box;
  #firstPoint;
  #lastPoint;
  #verticalEdges = [];
  #intervals = [];
  constructor(boxes, borderWidth = 0, innerMargin = 0, isLTR = true) {
    const minMax = BBOX_INIT.slice();
    const NUMBER_OF_DIGITS = 4;
    const EPSILON = 10 ** -NUMBER_OF_DIGITS;
    for (const {
      x,
      y,
      width,
      height
    } of boxes) {
      const x1 = Math.floor((x - borderWidth) / EPSILON) * EPSILON;
      const x2 = Math.ceil((x + width + borderWidth) / EPSILON) * EPSILON;
      const y1 = Math.floor((y - borderWidth) / EPSILON) * EPSILON;
      const y2 = Math.ceil((y + height + borderWidth) / EPSILON) * EPSILON;
      const left = [x1, y1, y2, true];
      const right = [x2, y1, y2, false];
      this.#verticalEdges.push(left, right);
      Util.rectBoundingBox(x1, y1, x2, y2, minMax);
    }
    const bboxWidth = minMax[2] - minMax[0] + 2 * innerMargin;
    const bboxHeight = minMax[3] - minMax[1] + 2 * innerMargin;
    const shiftedMinX = minMax[0] - innerMargin;
    const shiftedMinY = minMax[1] - innerMargin;
    let firstPointX = isLTR ? -Infinity : Infinity;
    let firstPointY = Infinity;
    const lastEdge = this.#verticalEdges.at(isLTR ? -1 : -2);
    const lastPoint = [lastEdge[0], lastEdge[2]];
    for (const edge of this.#verticalEdges) {
      const [x, y1, y2, left] = edge;
      if (!left && isLTR) {
        if (y1 < firstPointY) {
          firstPointY = y1;
          firstPointX = x;
        } else if (y1 === firstPointY) {
          firstPointX = Math.max(firstPointX, x);
        }
      } else if (left && !isLTR) {
        if (y1 < firstPointY) {
          firstPointY = y1;
          firstPointX = x;
        } else if (y1 === firstPointY) {
          firstPointX = Math.min(firstPointX, x);
        }
      }
      edge[0] = (x - shiftedMinX) / bboxWidth;
      edge[1] = (y1 - shiftedMinY) / bboxHeight;
      edge[2] = (y2 - shiftedMinY) / bboxHeight;
    }
    this.#box = new Float32Array([shiftedMinX, shiftedMinY, bboxWidth, bboxHeight]);
    this.#firstPoint = [firstPointX, firstPointY];
    this.#lastPoint = lastPoint;
  }
  getOutlines() {
    this.#verticalEdges.sort((a, b) => a[0] - b[0] || a[1] - b[1] || a[2] - b[2]);
    const outlineVerticalEdges = [];
    for (const edge of this.#verticalEdges) {
      if (edge[3]) {
        outlineVerticalEdges.push(...this.#breakEdge(edge));
        this.#insert(edge);
      } else {
        this.#remove(edge);
        outlineVerticalEdges.push(...this.#breakEdge(edge));
      }
    }
    return this.#getOutlines(outlineVerticalEdges);
  }
  #getOutlines(outlineVerticalEdges) {
    const edges = [];
    const allEdges = new Set();
    for (const edge of outlineVerticalEdges) {
      const [x, y1, y2] = edge;
      edges.push([x, y1, edge], [x, y2, edge]);
    }
    edges.sort((a, b) => a[1] - b[1] || a[0] - b[0]);
    for (let i = 0, ii = edges.length; i < ii; i += 2) {
      const edge1 = edges[i][2];
      const edge2 = edges[i + 1][2];
      edge1.push(edge2);
      edge2.push(edge1);
      allEdges.add(edge1);
      allEdges.add(edge2);
    }
    const outlines = [];
    while (allEdges.size > 0) {
      const edge = allEdges.values().next().value;
      let [x, y1, y2, edge1, edge2] = edge;
      allEdges.delete(edge);
      let lastPointX = x;
      let lastPointY = y1;
      const outline = [x, y2];
      outlines.push(outline);
      while (true) {
        let e;
        if (allEdges.has(edge1)) {
          e = edge1;
        } else if (allEdges.has(edge2)) {
          e = edge2;
        } else {
          break;
        }
        allEdges.delete(e);
        [x, y1, y2, edge1, edge2] = e;
        if (lastPointX !== x) {
          outline.push(lastPointX, lastPointY, x, lastPointY === y1 ? y1 : y2);
          lastPointX = x;
        }
        lastPointY = lastPointY === y1 ? y2 : y1;
      }
      outline.push(lastPointX, lastPointY);
    }
    return new HighlightOutline(outlines, this.#box, this.#firstPoint, this.#lastPoint);
  }
  #binarySearch(y) {
    const array = this.#intervals;
    let start = 0;
    let end = array.length - 1;
    while (start <= end) {
      const middle = start + end >> 1;
      const y1 = array[middle][0];
      if (y1 === y) {
        return middle;
      }
      if (y1 < y) {
        start = middle + 1;
      } else {
        end = middle - 1;
      }
    }
    return end + 1;
  }
  #insert([, y1, y2]) {
    const index = this.#binarySearch(y1);
    this.#intervals.splice(index, 0, [y1, y2]);
  }
  #remove([, y1, y2]) {
    const index = this.#binarySearch(y1);
    for (let i = index; i < this.#intervals.length; i++) {
      const [start, end] = this.#intervals[i];
      if (start !== y1) {
        break;
      }
      if (start === y1 && end === y2) {
        this.#intervals.splice(i, 1);
        return;
      }
    }
    for (let i = index - 1; i >= 0; i--) {
      const [start, end] = this.#intervals[i];
      if (start !== y1) {
        break;
      }
      if (start === y1 && end === y2) {
        this.#intervals.splice(i, 1);
        return;
      }
    }
  }
  #breakEdge(edge) {
    const [x, y1, y2] = edge;
    const results = [[x, y1, y2]];
    const index = this.#binarySearch(y2);
    for (let i = 0; i < index; i++) {
      const [start, end] = this.#intervals[i];
      for (let j = 0, jj = results.length; j < jj; j++) {
        const [, y3, y4] = results[j];
        if (end <= y3 || y4 <= start) {
          continue;
        }
        if (y3 >= start) {
          if (y4 > end) {
            results[j][1] = end;
          } else {
            if (jj === 1) {
              return [];
            }
            results.splice(j, 1);
            j--;
            jj--;
          }
          continue;
        }
        results[j][2] = start;
        if (y4 > end) {
          results.push([x, end, y4]);
        }
      }
    }
    return results;
  }
}
class HighlightOutline extends Outline {
  #box;
  #boxes = null;
  #outlines;
  constructor(outlines, box, firstPoint, lastPoint) {
    super();
    this.#outlines = outlines;
    this.#box = box;
    this.firstPoint = firstPoint;
    this.lastPoint = lastPoint;
  }
  static build(boxes, isLTR) {
    const outline = new HighlightOutliner(boxes, 0.001).getOutlines();
    outline.#boxes = boxes;
    outline.focusOutline = new HighlightOutliner(boxes, 0.0025, 0.001, isLTR).getOutlines();
    return outline;
  }
  get isFree() {
    return false;
  }
  get defaultSVGProperties() {
    return getHighlightSVGProperties(this);
  }
  getFocusSVGProperties(rotation) {
    return getHighlightFocusSVGProperties(this, rotation);
  }
  updateRotation(rotation) {
    return {
      root: {
        "data-main-rotation": rotation
      }
    };
  }
  serializeQuadPoints([pageX, pageY], [pageWidth, pageHeight]) {
    const boxes = this.#boxes;
    const quadPoints = new Float32Array(boxes.length * 8);
    let i = 0;
    for (const {
      x,
      y,
      width,
      height
    } of boxes) {
      const sx = x * pageWidth + pageX;
      const sy = (1 - y) * pageHeight + pageY;
      quadPoints[i] = quadPoints[i + 4] = sx;
      quadPoints[i + 1] = quadPoints[i + 3] = sy;
      quadPoints[i + 2] = quadPoints[i + 6] = sx + width * pageWidth;
      quadPoints[i + 5] = quadPoints[i + 7] = sy - height * pageHeight;
      i += 8;
    }
    return quadPoints;
  }
  toSVGPath() {
    const buffer = [];
    for (const polygon of this.#outlines) {
      let [prevX, prevY] = polygon;
      buffer.push(`M${prevX} ${prevY}`);
      for (let i = 2; i < polygon.length; i += 2) {
        const x = polygon[i];
        const y = polygon[i + 1];
        if (x === prevX) {
          buffer.push(`V${y}`);
          prevY = y;
        } else if (y === prevY) {
          buffer.push(`H${x}`);
          prevX = x;
        }
      }
      buffer.push("Z");
    }
    return buffer.join(" ");
  }
  serialize([blX, blY, trX, trY], _rotation) {
    const outlines = [];
    const width = trX - blX;
    const height = trY - blY;
    for (const outline of this.#outlines) {
      const points = new Array(outline.length);
      for (let i = 0; i < outline.length; i += 2) {
        points[i] = blX + outline[i] * width;
        points[i + 1] = trY - outline[i + 1] * height;
      }
      outlines.push(points);
    }
    return outlines;
  }
  get box() {
    return this.#box;
  }
}
class FreeHighlightOutliner extends FreeDrawOutliner {
  newFreeDrawOutline(outline, points, box, scaleFactor, innerMargin, isLTR) {
    return new FreeHighlightOutline(outline, points, box, scaleFactor, innerMargin, isLTR);
  }
}
class FreeHighlightDrawer {
  #outliner;
  #thickness;
  constructor(x, y, box, scaleFactor, thickness, isLTR, innerMargin) {
    this.#outliner = new FreeHighlightOutliner(x, y, box, scaleFactor, thickness, isLTR, innerMargin);
    this.#thickness = thickness;
  }
  add(x, y) {
    return this.#outliner.add(x, y) ? {
      path: {
        d: this.#outliner.toSVGPath()
      }
    } : null;
  }
  addPoints(points) {
    let hasChanged = false;
    for (let i = 0, ii = points.length; i < ii; i += 2) {
      hasChanged = this.#outliner.add(points[i], points[i + 1]) || hasChanged;
    }
    return hasChanged ? {
      path: {
        d: this.#outliner.toSVGPath()
      }
    } : null;
  }
  end(x, y) {
    return x === undefined ? null : this.add(x, y);
  }
  isEmpty() {
    return this.#outliner.isEmpty();
  }
  isCancellable() {
    return this.#outliner.isCancellable();
  }
  removeLastElement() {
    return this.#outliner.removeLastElement();
  }
  updateProperty(_name, _value) {
    return null;
  }
  getOutlines() {
    const outlines = this.#outliner.getOutlines();
    outlines.buildFocusOutline(2 * this.#thickness);
    return outlines;
  }
  get defaultSVGProperties() {
    return {
      bbox: [0, 0, 1, 1],
      root: {
        viewBox: "0 0 1 1"
      },
      rootClass: {
        highlight: true,
        free: true
      },
      path: {
        d: this.#outliner.toSVGPath()
      }
    };
  }
}
class FreeHighlightOutline extends FreeDrawOutline {
  static #EXTRA_THICKNESS = 1.5;
  newOutliner(x, y, box, scaleFactor, thickness, isLTR, innerMargin = 0) {
    return new FreeHighlightOutliner(x, y, box, scaleFactor, thickness, isLTR, innerMargin);
  }
  get isFree() {
    return true;
  }
  buildFocusOutline(thickness) {
    this.focusOutline = this.getNewOutline(thickness / 2 + FreeHighlightOutline.#EXTRA_THICKNESS, 0.0025);
  }
  get defaultSVGProperties() {
    return getHighlightSVGProperties(this);
  }
  getFocusSVGProperties(rotation) {
    return getHighlightFocusSVGProperties(this, rotation);
  }
  get focusMustRemoveSelfIntersections() {
    return true;
  }
  updateRotation(rotation) {
    return {
      root: {
        "data-main-rotation": rotation
      }
    };
  }
  updateProperty(name, value) {
    if (name !== "thickness") {
      return null;
    }
    const bbox = this.updateThickness(value / 2);
    this.buildFocusOutline(value);
    return bbox;
  }
  getPathResizedSVGProperties() {
    return {
      path: {
        d: this.toSVGPath()
      }
    };
  }
}

;// ./src/display/editor/highlight.js








class HighlightDrawingOptions extends DrawingOptions {
  constructor(properties = null) {
    super();
    super.updateProperties(properties);
  }
  updateSVGProperty(name, value) {
    if (name !== "thickness") {
      super.updateSVGProperty(name, value);
    }
  }
  clone() {
    const clone = new HighlightDrawingOptions();
    clone.updateAll(this);
    return clone;
  }
}
class HighlightEditor extends DrawingEditor {
  #anchorNode = null;
  #anchorOffset = 0;
  #focusNode = null;
  #focusOffset = 0;
  #methodOfCreation = "";
  #text = "";
  static _DEFAULT_OPACITY = 1;
  static _DEFAULT_THICKNESS = 12;
  static _defaultDrawingOptions = null;
  static _type = "highlight";
  static _editorType = AnnotationEditorType.HIGHLIGHT;
  static get _keyboardManager() {
    const proto = HighlightEditor.prototype;
    return shadow(this, "_keyboardManager", new KeyboardManager([[["ArrowLeft"], proto._moveCaret, {
      args: [0]
    }], [["ArrowRight"], proto._moveCaret, {
      args: [1]
    }], [["ArrowUp"], proto._moveCaret, {
      args: [2]
    }], [["ArrowDown"], proto._moveCaret, {
      args: [3]
    }]]));
  }
  constructor(params) {
    super({
      ...params,
      name: "highlightEditor"
    });
    this.#anchorNode = params.anchorNode || null;
    this.#anchorOffset = params.anchorOffset || 0;
    this.#focusNode = params.focusNode || null;
    this.#focusOffset = params.focusOffset || 0;
    this.#methodOfCreation = params.methodOfCreation || (this._drawOutlines?.isFree ? "main_toolbar" : "");
    this.#text = params.text || "";
    this._isDraggable = false;
    this.defaultL10nId = "pdfjs-editor-highlight-editor";
    this.rotate();
  }
  static initialize(l10n, uiManager) {
    AnnotationEditor.initialize(l10n, uiManager);
    this._defaultDrawingOptions ||= new HighlightDrawingOptions({
      fill: uiManager.highlightColors?.values().next().value || "#fff066",
      "fill-opacity": HighlightEditor._DEFAULT_OPACITY,
      thickness: HighlightEditor._DEFAULT_THICKNESS
    });
  }
  static getDefaultDrawingOptions(options) {
    const clone = this._defaultDrawingOptions.clone();
    clone.updateProperties(options);
    return clone;
  }
  static get typesMap() {
    return shadow(this, "typesMap", new Map([[AnnotationEditorParamsType.HIGHLIGHT_COLOR, "fill"], [AnnotationEditorParamsType.HIGHLIGHT_THICKNESS, "thickness"]]));
  }
  static get isDrawer() {
    return false;
  }
  static get _hasClipPath() {
    return true;
  }
  static get _hasDrawClass() {
    return false;
  }
  _addOutlines(params) {
    const {
      boxes,
      drawOutlines
    } = params;
    if (!boxes && !drawOutlines) {
      return;
    }
    this._drawingOptions ||= params.drawingOptions || HighlightEditor.getDefaultDrawingOptions();
    if (boxes) {
      params = {
        ...params,
        drawOutlines: HighlightOutline.build(boxes, this._uiManager.direction === "ltr")
      };
    }
    super._addOutlines(params);
  }
  get colorType() {
    return AnnotationEditorParamsType.HIGHLIGHT_COLOR;
  }
  get color() {
    return this._drawingOptions.fill;
  }
  get opacity() {
    return this._drawingOptions["fill-opacity"];
  }
  get _opacityName() {
    return "fill-opacity";
  }
  get _drawRotation() {
    return this._drawOutlines?.isFree ? this.rotation : 0;
  }
  get isResizable() {
    return false;
  }
  get _mustBeDisabledOnCommit() {
    return false;
  }
  get _mustFixPosition() {
    return !this._drawOutlines?.isFree;
  }
  get telemetryInitialData() {
    return {
      action: "added",
      type: this._drawOutlines.isFree ? "free_highlight" : "highlight",
      color: this._uiManager.getNonHCMColorName(this.color),
      thickness: this._drawingOptions.thickness,
      methodOfCreation: this.#methodOfCreation
    };
  }
  get telemetryFinalData() {
    return {
      type: "highlight",
      color: this._uiManager.getNonHCMColorName(this.color)
    };
  }
  static computeTelemetryFinalData(data) {
    return {
      numberOfColors: data.get("color").size
    };
  }
  translateInPage(x, y) {}
  get toolbarPosition() {
    return this.#relativeToBox(this._drawOutlines.focusOutline.lastPoint);
  }
  get commentButtonPosition() {
    return this.#relativeToBox(this._drawOutlines.firstPoint);
  }
  #relativeToBox([pointX, pointY]) {
    const [x, y, width, height] = this._drawOutlines.box;
    return [(pointX - x) / width, (pointY - y) / height];
  }
  updateParams(type, value) {
    switch (type) {
      case AnnotationEditorParamsType.HIGHLIGHT_COLOR:
        this._updateColorAndOpacity(value, HighlightEditor._DEFAULT_OPACITY, type);
        this._reportTelemetry({
          action: "color_changed",
          color: this._uiManager.getNonHCMColorName(value)
        }, true);
        break;
      case AnnotationEditorParamsType.HIGHLIGHT_THICKNESS:
        super.updateParams(type, value);
        this._reportTelemetry({
          action: "thickness_changed",
          thickness: value
        }, true);
        break;
    }
  }
  get propertiesToUpdate() {
    const properties = super.propertiesToUpdate;
    properties.push([AnnotationEditorParamsType.HIGHLIGHT_FREE, this._drawOutlines.isFree]);
    return properties;
  }
  get toolbarButtons() {
    if (this._uiManager.highlightColors) {
      this._colorPicker = new ColorPicker({
        editor: this
      });
      return [["colorPicker", this._colorPicker]];
    }
    return super.toolbarButtons;
  }
  fixAndSetPosition() {
    return super.fixAndSetPosition(this._drawRotation);
  }
  getRect(tx, ty) {
    return super.getRect(tx, ty, this._drawRotation);
  }
  onceAdded(focus) {
    if (!this.annotationElementId) {
      this.parent.addUndoableEditor(this);
    }
    if (focus) {
      this.div.focus();
    }
  }
  remove() {
    this._reportTelemetry({
      action: "deleted"
    });
    super.remove();
  }
  render() {
    if (this.div) {
      return this.div;
    }
    const div = super.render();
    if (this.#text) {
      div.setAttribute("aria-label", this.#text);
      div.setAttribute("role", "mark");
    }
    if (this._drawOutlines.isFree) {
      div.classList.add("free");
    } else {
      div.addEventListener("keydown", this.#keydown.bind(this), {
        signal: this._uiManager._signal
      });
    }
    this.enableEditing();
    return div;
  }
  #keydown(event) {
    HighlightEditor._keyboardManager.exec(this, event);
  }
  _moveCaret(direction) {
    this.parent.unselect(this);
    switch (direction) {
      case 0:
      case 2:
        this.#setCaret(true);
        break;
      case 1:
      case 3:
        this.#setCaret(false);
        break;
    }
  }
  #setCaret(start) {
    if (!this.#anchorNode) {
      return;
    }
    const selection = window.getSelection();
    if (start) {
      selection.setPosition(this.#anchorNode, this.#anchorOffset);
    } else {
      selection.setPosition(this.#focusNode, this.#focusOffset);
    }
  }
  unselect() {
    super.unselect();
    if (!this._drawOutlines.isFree) {
      this.#setCaret(false);
    }
  }
  static createDrawerInstance({
    x,
    y,
    box,
    parent,
    isLTR
  }) {
    return new FreeHighlightDrawer(x, y, box, parent.scale, this._defaultDrawingOptions.thickness / 2, isLTR, 0.001);
  }
  static _getDrawingTarget(parent, {
    target
  }) {
    return target.closest(".textLayer");
  }
  static _getPointerCoords({
    x,
    y
  }) {
    return [x, y];
  }
  static _addDrawingListeners(target, signal) {
    target.classList.add("free");
    signal.addEventListener("abort", () => target.classList.remove("free"), {
      once: true
    });
    window.addEventListener("blur", () => this._endDraw(null), {
      signal
    });
    window.addEventListener("pointerdown", stopEvent, {
      capture: true,
      passive: false,
      signal
    });
  }
  static _endDrawingSession(isAborted = false) {
    return this.endDrawing(isAborted);
  }
  createDrawingOptions({
    color,
    opacity,
    thickness
  }) {
    const {
      _defaultDrawingOptions: defaults,
      _DEFAULT_OPACITY
    } = HighlightEditor;
    this._drawingOptions = HighlightEditor.getDefaultDrawingOptions({
      fill: Util.makeHexColor(...color),
      "fill-opacity": opacity || _DEFAULT_OPACITY,
      thickness: thickness || defaults.thickness
    });
  }
  static deserializeDraw(pageX, pageY, pageWidth, pageHeight, _innerMargin, data, uiManager) {
    const {
      quadPoints
    } = data;
    if (quadPoints) {
      const boxes = [];
      for (let i = 0, ii = quadPoints.length; i < ii; i += 8) {
        boxes.push({
          x: (quadPoints[i] - pageX) / pageWidth,
          y: 1 - (quadPoints[i + 1] - pageY) / pageHeight,
          width: (quadPoints[i + 2] - quadPoints[i]) / pageWidth,
          height: (quadPoints[i + 1] - quadPoints[i + 5]) / pageHeight
        });
      }
      return HighlightOutline.build(boxes, uiManager.direction === "ltr");
    }
    const thickness = data.thickness || this._defaultDrawingOptions.thickness;
    const points = (data.inkLists || data.outlines.points)[0];
    const outliner = new FreeHighlightOutliner(points[0] - pageX, pageHeight - (points[1] - pageY), [0, 0, pageWidth, pageHeight], 1, thickness / 2, true, 0.001);
    for (let i = 0, ii = points.length; i < ii; i += 2) {
      outliner.add(points[i] - pageX, pageHeight - (points[i + 1] - pageY));
    }
    const outlines = outliner.getOutlines();
    outlines.buildFocusOutline(thickness);
    return outlines;
  }
  static async deserialize(data, parent, uiManager) {
    let initialData = null;
    if (data instanceof HighlightAnnotationElement) {
      const {
        data: {
          quadPoints,
          rect,
          rotation,
          id,
          color,
          opacity,
          popupRef,
          richText,
          contentsObj,
          creationDate,
          modificationDate
        },
        parent: {
          page: {
            pageNumber
          }
        }
      } = data;
      initialData = data = {
        annotationType: AnnotationEditorType.HIGHLIGHT,
        color: Array.from(color),
        opacity,
        quadPoints,
        pageIndex: pageNumber - 1,
        rect: rect.slice(0),
        rotation,
        annotationElementId: id,
        id,
        deleted: false,
        popupRef,
        richText,
        comment: contentsObj?.str || null,
        creationDate,
        modificationDate
      };
    } else if (data instanceof InkAnnotationElement) {
      const {
        data: {
          inkLists,
          rect,
          rotation,
          id,
          color,
          borderStyle: {
            rawWidth: thickness
          },
          popupRef,
          richText,
          contentsObj,
          creationDate,
          modificationDate
        },
        parent: {
          page: {
            pageNumber
          }
        }
      } = data;
      initialData = data = {
        annotationType: AnnotationEditorType.HIGHLIGHT,
        color: Array.from(color),
        thickness,
        inkLists,
        pageIndex: pageNumber - 1,
        rect: rect.slice(0),
        rotation,
        annotationElementId: id,
        id,
        deleted: false,
        popupRef,
        richText,
        comment: contentsObj?.str || null,
        creationDate,
        modificationDate
      };
    }
    const editor = await super.deserialize(data, parent, uiManager);
    editor._initialData = initialData;
    if (data.comment) {
      editor.setCommentData(data);
    }
    return editor;
  }
  serialize(isForCopying = false) {
    if (this.isEmpty() || isForCopying) {
      return null;
    }
    if (this.deleted) {
      return this.serializeDeleted();
    }
    const serialized = super.serialize(isForCopying);
    Object.assign(serialized, {
      color: AnnotationEditor._colorManager.convert(this._uiManager.getNonHCMColor(this.color)),
      opacity: this.opacity,
      thickness: this._drawingOptions.thickness,
      quadPoints: this._drawOutlines.serializeQuadPoints(this.pageTranslation, this.pageDimensions),
      outlines: this._drawOutlines.serialize(serialized.rect, this._drawRotation)
    });
    this.addComment(serialized);
    if (this.annotationElementId && !this.#hasElementChanged(serialized)) {
      return null;
    }
    serialized.id = this.annotationElementId;
    return serialized;
  }
  #hasElementChanged(serialized) {
    const {
      color
    } = this._initialData;
    return this.hasEditedComment || serialized.color.some((c, i) => c !== color[i]);
  }
  renderAnnotationElement(annotation) {
    if (this.deleted) {
      annotation.hide();
      return null;
    }
    annotation.updateEdited({
      rect: this.getPDFRect(),
      popup: this.comment
    });
    return null;
  }
}

;// ./src/display/editor/drawers/input_smoother.js
class InputSmoother {
  static #HALF_WINDOW = 10;
  static #UPSAMPLING_PERIOD = 1000 / 180;
  static #MAX_DIVISIONS = 100;
  static #TIME_EPSILON = 1e-3;
  #samples;
  #firstTime;
  #lastTime;
  constructor(x, y, timeStamp) {
    this.#samples = [x, y, timeStamp];
    this.#firstTime = this.#lastTime = timeStamp;
  }
  add(x, y, timeStamp) {
    const samples = this.#samples;
    const lastTime = samples.at(-1);
    timeStamp = timeStamp > lastTime ? timeStamp : lastTime + InputSmoother.#TIME_EPSILON;
    samples.push(x, y, timeStamp);
    const points = this.#smooth(timeStamp - InputSmoother.#HALF_WINDOW, true);
    const start = this.#getSampleIndex(this.#lastTime - InputSmoother.#HALF_WINDOW);
    if (start >= samples.length / 2) {
      samples.copyWithin(0, start);
      samples.length -= start;
    }
    return points;
  }
  get pendingPoints() {
    return this.#smooth(Infinity, false);
  }
  end() {
    return this.#smooth(Infinity, true);
  }
  #smooth(maxTime, isStable) {
    const samples = this.#samples;
    const firstTime = this.#firstTime;
    const lastTime = samples.at(-1);
    const points = [];
    const time = this.#lastTime;
    for (let i = this.#getSampleIndex(time) + 3; i < samples.length; i += 3) {
      const startTime = samples[i - 1];
      const dt = samples[i + 2] - startTime;
      const n = Math.min(Math.ceil(dt / InputSmoother.#UPSAMPLING_PERIOD), InputSmoother.#MAX_DIVISIONS);
      for (let k = 1; k <= n; k++) {
        const t = k === n ? samples[i + 2] : startTime + dt * k / n;
        if (t <= time) {
          continue;
        }
        if (t > maxTime) {
          return points;
        }
        const halfWindow = Math.min(InputSmoother.#HALF_WINDOW, t - firstTime, lastTime - t);
        this.#average(t - halfWindow, t + halfWindow, points);
        if (isStable) {
          this.#lastTime = t;
        }
      }
    }
    return points;
  }
  #getSampleIndex(time) {
    const samples = this.#samples;
    let start = 0;
    let end = samples.length / 3 - 1;
    while (start < end) {
      const middle = start + end + 1 >> 1;
      if (samples[3 * middle + 2] <= time) {
        start = middle;
      } else {
        end = middle - 1;
      }
    }
    return 3 * start;
  }
  #average(startTime, endTime, points) {
    const samples = this.#samples;
    const index = this.#getSampleIndex(startTime);
    let sumX = 0,
      sumY = 0,
      duration = 0;
    for (let i = index; i < samples.length - 3 && samples[i + 2] < endTime; i += 3) {
      const x1 = samples[i],
        y1 = samples[i + 1],
        t1 = samples[i + 2],
        t2 = samples[i + 5];
      const start = Math.max(t1, startTime);
      const end = Math.min(t2, endTime);
      if (end <= start) {
        continue;
      }
      const dt = end - start;
      const ratio = (start + end - 2 * t1) / (t2 - t1);
      sumX += dt * (x1 + ratio * (samples[i + 3] - x1) / 2);
      sumY += dt * (y1 + ratio * (samples[i + 4] - y1) / 2);
      duration += dt;
    }
    if (duration === 0) {
      points.push(samples[index], samples[index + 1]);
    } else {
      points.push(sumX / duration, sumY / duration);
    }
  }
}

;// ./src/display/editor/drawers/inkdraw.js




function svgPoint(data, i) {
  return `${Outline.svgRound(data[i])} ${Outline.svgRound(data[i + 1])}`;
}
function pushCurves(buffer, line, start) {
  for (let i = start, ii = line.length; i < ii; i += 6) {
    buffer.push(`C${svgPoint(line, i)} ${svgPoint(line, i + 2)} ${svgPoint(line, i + 4)}`);
  }
}
function lineToSVGPath(line) {
  const start = `M${svgPoint(line, 4)}`;
  if (line.length === 6) {
    return `${start}Z`;
  }
  if (line.length === 12 && isNaN(line[6])) {
    return `${start}L${svgPoint(line, 10)}`;
  }
  const buffer = [start];
  pushCurves(buffer, line, 6);
  return buffer.join("");
}
class InkDrawOutliner {
  #last = new Float64Array(6);
  #tip = new Float64Array(2);
  #line;
  #lines;
  #rotation;
  #smoother = null;
  #thickness;
  #points;
  #inputCount = 1;
  #lastInput = new Float64Array(2);
  #lastSVGPath = "";
  #lastIndex = 0;
  #outlines = new InkDrawOutline();
  #parentWidth;
  #parentHeight;
  constructor(x, y, parentWidth, parentHeight, rotation, thickness, timeStamp) {
    this.#parentWidth = parentWidth;
    this.#parentHeight = parentHeight;
    this.#rotation = rotation;
    this.#thickness = thickness;
    this.#lines = [];
    this.#startLine(x, y, timeStamp);
  }
  #startLine(x, y, timeStamp) {
    [x, y] = this.#normalizeToTip(x, y);
    const line = this.#line = [NaN, NaN, NaN, NaN, x, y];
    this.#points = [x, y];
    this.#lines.push({
      line,
      points: this.#points
    });
    this.#last.set(line, 0);
    this.#lastIndex = 0;
    this.#inputCount = 1;
    this.#lastInput.set(this.#tip);
    this.#smoother = timeStamp === undefined ? null : new InputSmoother(x, y, timeStamp);
  }
  updateProperty(name, value) {
    if (name === "stroke-width") {
      this.#thickness = value;
    }
  }
  #normalizeToTip(x, y) {
    return Outline._normalizePoint(x, y, this.#parentWidth, this.#parentHeight, this.#rotation, this.#tip);
  }
  isEmpty() {
    return !this.#lines?.length;
  }
  isCancellable() {
    return this.#inputCount <= 5;
  }
  add(x, y, timeStamp) {
    this.#addSample(x, y, timeStamp);
    return {
      path: {
        d: this.#toSVGPathWithTip()
      }
    };
  }
  addPoints(points, timeStamps) {
    for (let i = 0, ii = points.length; i < ii; i += 2) {
      this.#addSample(points[i], points[i + 1], timeStamps?.[i / 2]);
    }
    return {
      path: {
        d: this.#toSVGPathWithTip()
      }
    };
  }
  #addSample(x, y, timeStamp) {
    [x, y] = this.#normalizeToTip(x, y);
    const [lastX, lastY] = this.#lastInput;
    if (!this.#isTooClose(x, y, lastX, lastY)) {
      this.#inputCount++;
      this.#lastInput.set(this.#tip);
    }
    if (this.#smoother) {
      this.#addSmoothedPoints(this.#smoother.add(x, y, timeStamp));
    } else {
      this.#addPoint(x, y);
    }
  }
  #isTooClose(x, y, lastX, lastY) {
    return Math.hypot(this.#parentWidth * (x - lastX), this.#parentHeight * (y - lastY)) <= 2;
  }
  #addSmoothedPoints(points) {
    for (let i = 0, ii = points.length; i < ii; i += 2) {
      this.#addPoint(points[i], points[i + 1]);
    }
  }
  #addPoint(x, y) {
    const [,, x1, y1, x2, y2] = this.#last;
    if (this.#isTooClose(x, y, x2, y2)) {
      return;
    }
    this.#points.push(x, y);
    if (isNaN(x1)) {
      this.#line.push(NaN, NaN, NaN, NaN, x, y);
    } else {
      if (isNaN(this.#last[0])) {
        this.#line.splice(6, 6);
      }
      Outline.createBezierPoints(x1, y1, x2, y2, x, y, this.#line);
    }
    this.#last.copyWithin(0, 2);
    this.#last[4] = x;
    this.#last[5] = y;
  }
  #updatePath() {
    const line = this.#line;
    if (this.#points.length < 6 || this.#lastIndex === line.length) {
      return;
    }
    const buffer = [this.#lastSVGPath];
    if (this.#lastIndex === 0) {
      buffer.push(`M${svgPoint(line, 4)}`);
      this.#lastIndex = 6;
    }
    pushCurves(buffer, line, this.#lastIndex);
    this.#lastSVGPath = buffer.join("");
    this.#lastIndex = line.length;
  }
  #endLine() {
    if (!this.#line) {
      return;
    }
    if (this.#smoother) {
      this.#addSmoothedPoints(this.#smoother.end());
      this.#smoother = null;
    }
    if (this.#points.length < 6) {
      this.#lastSVGPath += lineToSVGPath(this.#line);
    } else {
      const [,, x1, y1, x2, y2] = this.#last;
      Outline.createBezierPoints(x1, y1, x2, y2, x2, y2, this.#line);
      this.#updatePath();
    }
    this.#line = this.#points = null;
  }
  end(x, y, timeStamp) {
    if (this.#line && x !== undefined) {
      this.#addSample(x, y, timeStamp);
    }
    this.#endLine();
    return {
      path: {
        d: this.#lastSVGPath
      }
    };
  }
  startNew(x, y, parentWidth, parentHeight, rotation, timeStamp) {
    this.#parentWidth = parentWidth;
    this.#parentHeight = parentHeight;
    this.#rotation = rotation;
    const last = this.#lines.at(-1);
    if (last) {
      last.line = new Float32Array(last.line);
      last.points = new Float32Array(last.points);
    }
    this.#startLine(x, y, timeStamp);
    return null;
  }
  getLastElement() {
    return this.#lines.at(-1);
  }
  setLastElement(element) {
    if (!this.#lines) {
      return this.#outlines.setLastElement(element);
    }
    this.#lines.push(element);
    this.#lastSVGPath += lineToSVGPath(element.line);
    return {
      path: {
        d: this.#lastSVGPath
      }
    };
  }
  removeLastElement() {
    if (!this.#lines) {
      return this.#outlines.removeLastElement();
    }
    this.#line = this.#points = this.#smoother = null;
    this.#lines.pop();
    this.#lastSVGPath = this.#lines.map(({
      line
    }) => lineToSVGPath(line)).join("");
    return {
      path: {
        d: this.#lastSVGPath
      }
    };
  }
  #toSVGPathWithTip() {
    this.#updatePath();
    const buffer = [this.#lastSVGPath];
    if (this.#lastIndex === 0) {
      buffer.push(`M${svgPoint(this.#line, 4)}`);
      if (this.#points.length === 4) {
        buffer.push(`L${svgPoint(this.#line, 10)}`);
      }
    }
    let points = this.#smoother?.pendingPoints;
    if (!points?.length) {
      points = this.#tip;
    }
    for (let i = 0, ii = points.length; i < ii; i += 2) {
      buffer.push(`L${svgPoint(points, i)}`);
    }
    return buffer.join("");
  }
  getOutlines(parentWidth, parentHeight, scale, innerMargin) {
    this.#endLine();
    const last = this.#lines.at(-1);
    last.line = new Float32Array(last.line);
    last.points = new Float32Array(last.points);
    this.#outlines.build(this.#lines, parentWidth, parentHeight, scale, this.#rotation, this.#thickness, innerMargin);
    this.#last = null;
    this.#line = null;
    this.#lines = null;
    this.#lastSVGPath = null;
    return this.#outlines;
  }
  get defaultSVGProperties() {
    return {
      root: {
        viewBox: "0 0 10000 10000"
      },
      rootClass: {
        draw: true
      },
      bbox: [0, 0, 1, 1]
    };
  }
}
class InkDrawOutline extends Outline {
  #bbox;
  #currentRotation = 0;
  #innerMargin;
  #lines;
  #parentWidth;
  #parentHeight;
  #parentScale;
  #rotation;
  #thickness;
  build(lines, parentWidth, parentHeight, parentScale, rotation, thickness, innerMargin) {
    this.#parentWidth = parentWidth;
    this.#parentHeight = parentHeight;
    this.#parentScale = parentScale;
    this.#rotation = rotation;
    this.#thickness = thickness;
    this.#innerMargin = innerMargin ?? 0;
    this.#lines = lines;
    this.#computeBbox();
  }
  get thickness() {
    return this.#thickness;
  }
  setLastElement(element) {
    this.#lines.push(element);
    return {
      path: {
        d: this.toSVGPath()
      }
    };
  }
  removeLastElement() {
    this.#lines.pop();
    return {
      path: {
        d: this.toSVGPath()
      }
    };
  }
  toSVGPath() {
    return this.#lines.map(({
      line
    }) => lineToSVGPath(line)).join("");
  }
  serialize([pageX, pageY, pageWidth, pageHeight], isForCopying) {
    const serializedLines = [];
    const serializedPoints = [];
    const [x, y, width, height] = this.#getBBoxWithNoMargin();
    let tx, ty, sx, sy, x1, y1, x2, y2, rescaleFn;
    switch (this.#rotation) {
      case 0:
        rescaleFn = Outline._rescale;
        tx = pageX;
        ty = pageY + pageHeight;
        sx = pageWidth;
        sy = -pageHeight;
        x1 = pageX + x * pageWidth;
        y1 = pageY + (1 - y - height) * pageHeight;
        x2 = pageX + (x + width) * pageWidth;
        y2 = pageY + (1 - y) * pageHeight;
        break;
      case 90:
        rescaleFn = Outline._rescaleAndSwap;
        tx = pageX;
        ty = pageY;
        sx = pageWidth;
        sy = pageHeight;
        x1 = pageX + y * pageWidth;
        y1 = pageY + x * pageHeight;
        x2 = pageX + (y + height) * pageWidth;
        y2 = pageY + (x + width) * pageHeight;
        break;
      case 180:
        rescaleFn = Outline._rescale;
        tx = pageX + pageWidth;
        ty = pageY;
        sx = -pageWidth;
        sy = pageHeight;
        x1 = pageX + (1 - x - width) * pageWidth;
        y1 = pageY + y * pageHeight;
        x2 = pageX + (1 - x) * pageWidth;
        y2 = pageY + (y + height) * pageHeight;
        break;
      case 270:
        rescaleFn = Outline._rescaleAndSwap;
        tx = pageX + pageWidth;
        ty = pageY + pageHeight;
        sx = -pageWidth;
        sy = -pageHeight;
        x1 = pageX + (1 - y - height) * pageWidth;
        y1 = pageY + (1 - x - width) * pageHeight;
        x2 = pageX + (1 - y) * pageWidth;
        y2 = pageY + (1 - x) * pageHeight;
        break;
    }
    for (const {
      line,
      points
    } of this.#lines) {
      serializedLines.push(rescaleFn(line, tx, ty, sx, sy, isForCopying ? new Array(line.length) : null));
      serializedPoints.push(rescaleFn(points, tx, ty, sx, sy, isForCopying ? new Array(points.length) : null));
    }
    return {
      lines: serializedLines,
      points: serializedPoints,
      rect: [x1, y1, x2, y2]
    };
  }
  static deserialize(pageX, pageY, pageWidth, pageHeight, innerMargin, {
    paths: {
      lines,
      points
    },
    rotation,
    thickness
  }) {
    const newLines = [];
    let tx, ty, sx, sy, rescaleFn;
    switch (rotation) {
      case 0:
        rescaleFn = Outline._rescale;
        tx = -pageX / pageWidth;
        ty = pageY / pageHeight + 1;
        sx = 1 / pageWidth;
        sy = -1 / pageHeight;
        break;
      case 90:
        rescaleFn = Outline._rescaleAndSwap;
        tx = -pageY / pageHeight;
        ty = -pageX / pageWidth;
        sx = 1 / pageHeight;
        sy = 1 / pageWidth;
        break;
      case 180:
        rescaleFn = Outline._rescale;
        tx = pageX / pageWidth + 1;
        ty = -pageY / pageHeight;
        sx = -1 / pageWidth;
        sy = 1 / pageHeight;
        break;
      case 270:
        rescaleFn = Outline._rescaleAndSwap;
        tx = pageY / pageHeight + 1;
        ty = pageX / pageWidth + 1;
        sx = -1 / pageHeight;
        sy = -1 / pageWidth;
        break;
    }
    if (!lines) {
      lines = [];
      for (const point of points) {
        const len = point.length;
        if (len === 2) {
          lines.push(new Float32Array([NaN, NaN, NaN, NaN, point[0], point[1]]));
          continue;
        }
        if (len === 4) {
          lines.push(new Float32Array([NaN, NaN, NaN, NaN, point[0], point[1], NaN, NaN, NaN, NaN, point[2], point[3]]));
          continue;
        }
        const line = new Float32Array(3 * len);
        lines.push(line);
        let [x1, y1, x2, y2] = point.subarray(0, 4);
        line.set([NaN, NaN, NaN, NaN, x1, y1], 0);
        for (let i = 4; i <= len; i += 2) {
          const j = Math.min(i, len - 2);
          const x = point[j];
          const y = point[j + 1];
          line.set(Outline.createBezierPoints(x1, y1, x2, y2, x, y), (i - 2) * 3);
          [x1, y1, x2, y2] = [x2, y2, x, y];
        }
      }
    }
    for (let i = 0, ii = lines.length; i < ii; i++) {
      newLines.push({
        line: rescaleFn(lines[i].map(x => x ?? NaN), tx, ty, sx, sy),
        points: rescaleFn(points[i].map(x => x ?? NaN), tx, ty, sx, sy)
      });
    }
    const outlines = new this.prototype.constructor();
    outlines.build(newLines, pageWidth, pageHeight, 1, rotation, thickness, innerMargin);
    return outlines;
  }
  #getMarginComponents(thickness = this.#thickness) {
    const margin = this.#innerMargin + thickness / 2 * this.#parentScale;
    return this.#rotation % 180 === 0 ? [margin / this.#parentWidth, margin / this.#parentHeight] : [margin / this.#parentHeight, margin / this.#parentWidth];
  }
  #getBBoxWithNoMargin() {
    const [x, y, width, height] = this.#bbox;
    const [marginX, marginY] = this.#getMarginComponents(0);
    return [x + marginX, y + marginY, width - 2 * marginX, height - 2 * marginY];
  }
  #computeBbox() {
    const bbox = this.#bbox = F32_BBOX_INIT.slice();
    for (const {
      line
    } of this.#lines) {
      if (line.length <= 12) {
        for (let i = 4, ii = line.length; i < ii; i += 6) {
          Util.pointBoundingBox(line[i], line[i + 1], bbox);
        }
        continue;
      }
      let lastX = line[4],
        lastY = line[5];
      for (let i = 6, ii = line.length; i < ii; i += 6) {
        const [c1x, c1y, c2x, c2y, x, y] = line.subarray(i, i + 6);
        Util.bezierBoundingBox(lastX, lastY, c1x, c1y, c2x, c2y, x, y, bbox);
        lastX = x;
        lastY = y;
      }
    }
    const [marginX, marginY] = this.#getMarginComponents();
    bbox[0] = MathClamp(bbox[0] - marginX, 0, 1);
    bbox[1] = MathClamp(bbox[1] - marginY, 0, 1);
    bbox[2] = MathClamp(bbox[2] + marginX, 0, 1);
    bbox[3] = MathClamp(bbox[3] + marginY, 0, 1);
    bbox[2] -= bbox[0];
    bbox[3] -= bbox[1];
  }
  get box() {
    return this.#bbox;
  }
  updateProperty(name, value) {
    return name === "stroke-width" ? this.#updateThickness(value) : null;
  }
  #updateThickness(thickness) {
    const [oldMarginX, oldMarginY] = this.#getMarginComponents();
    this.#thickness = thickness;
    const [newMarginX, newMarginY] = this.#getMarginComponents();
    const [diffMarginX, diffMarginY] = [newMarginX - oldMarginX, newMarginY - oldMarginY];
    const bbox = this.#bbox;
    bbox[0] -= diffMarginX;
    bbox[1] -= diffMarginY;
    bbox[2] += 2 * diffMarginX;
    bbox[3] += 2 * diffMarginY;
    return bbox;
  }
  updateParentDimensions([width, height], scale) {
    const [oldMarginX, oldMarginY] = this.#getMarginComponents();
    this.#parentWidth = width;
    this.#parentHeight = height;
    this.#parentScale = scale;
    const [newMarginX, newMarginY] = this.#getMarginComponents();
    const diffMarginX = newMarginX - oldMarginX;
    const diffMarginY = newMarginY - oldMarginY;
    const bbox = this.#bbox;
    bbox[0] -= diffMarginX;
    bbox[1] -= diffMarginY;
    bbox[2] += 2 * diffMarginX;
    bbox[3] += 2 * diffMarginY;
    return bbox;
  }
  updateRotation(rotation) {
    this.#currentRotation = rotation;
    return {
      path: {
        transform: this.rotationTransform
      }
    };
  }
  get viewBox() {
    return this.#bbox.map(Outline.svgRound).join(" ");
  }
  get defaultProperties() {
    const [x, y] = this.#bbox;
    return {
      root: {
        viewBox: this.viewBox
      },
      path: {
        "transform-origin": `${Outline.svgRound(x)} ${Outline.svgRound(y)}`
      }
    };
  }
  get rotationTransform() {
    const [,, width, height] = this.#bbox;
    let a = 0,
      b = 0,
      c = 0,
      d = 0,
      e = 0,
      f = 0;
    switch (this.#currentRotation) {
      case 90:
        b = height / width;
        c = -width / height;
        e = width;
        break;
      case 180:
        a = -1;
        d = -1;
        e = width;
        f = height;
        break;
      case 270:
        b = -height / width;
        c = width / height;
        f = height;
        break;
      default:
        return "";
    }
    return `matrix(${a} ${b} ${c} ${d} ${Outline.svgRound(e)} ${Outline.svgRound(f)})`;
  }
  getPathResizingSVGProperties([newX, newY, newWidth, newHeight]) {
    const [marginX, marginY] = this.#getMarginComponents();
    const [x, y, width, height] = this.#bbox;
    if (Math.abs(width - marginX) <= Outline.PRECISION || Math.abs(height - marginY) <= Outline.PRECISION) {
      const tx = newX + newWidth / 2 - (x + width / 2);
      const ty = newY + newHeight / 2 - (y + height / 2);
      return {
        path: {
          "transform-origin": `${Outline.svgRound(newX)} ${Outline.svgRound(newY)}`,
          transform: `${this.rotationTransform} translate(${tx} ${ty})`
        }
      };
    }
    const s1x = (newWidth - 2 * marginX) / (width - 2 * marginX);
    const s1y = (newHeight - 2 * marginY) / (height - 2 * marginY);
    const s2x = width / newWidth;
    const s2y = height / newHeight;
    return {
      path: {
        "transform-origin": `${Outline.svgRound(x)} ${Outline.svgRound(y)}`,
        transform: `${this.rotationTransform} scale(${s2x} ${s2y}) ` + `translate(${Outline.svgRound(marginX)} ${Outline.svgRound(marginY)}) scale(${s1x} ${s1y}) ` + `translate(${Outline.svgRound(-marginX)} ${Outline.svgRound(-marginY)})`
      }
    };
  }
  getPathResizedSVGProperties([newX, newY, newWidth, newHeight]) {
    const [marginX, marginY] = this.#getMarginComponents();
    const bbox = this.#bbox;
    const [x, y, width, height] = bbox;
    bbox[0] = newX;
    bbox[1] = newY;
    bbox[2] = newWidth;
    bbox[3] = newHeight;
    if (Math.abs(width - marginX) <= Outline.PRECISION || Math.abs(height - marginY) <= Outline.PRECISION) {
      const tx = newX + newWidth / 2 - (x + width / 2);
      const ty = newY + newHeight / 2 - (y + height / 2);
      for (const {
        line,
        points
      } of this.#lines) {
        Outline._translate(line, tx, ty, line);
        Outline._translate(points, tx, ty, points);
      }
      return {
        root: {
          viewBox: this.viewBox
        },
        path: {
          "transform-origin": `${Outline.svgRound(newX)} ${Outline.svgRound(newY)}`,
          transform: this.rotationTransform || null,
          d: this.toSVGPath()
        }
      };
    }
    const s1x = (newWidth - 2 * marginX) / (width - 2 * marginX);
    const s1y = (newHeight - 2 * marginY) / (height - 2 * marginY);
    const tx = -s1x * (x + marginX) + newX + marginX;
    const ty = -s1y * (y + marginY) + newY + marginY;
    if (s1x !== 1 || s1y !== 1 || tx !== 0 || ty !== 0) {
      for (const {
        line,
        points
      } of this.#lines) {
        Outline._rescale(line, tx, ty, s1x, s1y, line);
        Outline._rescale(points, tx, ty, s1x, s1y, points);
      }
    }
    return {
      root: {
        viewBox: this.viewBox
      },
      path: {
        "transform-origin": `${Outline.svgRound(newX)} ${Outline.svgRound(newY)}`,
        transform: this.rotationTransform || null,
        d: this.toSVGPath()
      }
    };
  }
  getPathTranslatedSVGProperties([newX, newY], parentDimensions) {
    const [newParentWidth, newParentHeight] = parentDimensions;
    const bbox = this.#bbox;
    const tx = newX - bbox[0];
    const ty = newY - bbox[1];
    if (this.#parentWidth === newParentWidth && this.#parentHeight === newParentHeight) {
      for (const {
        line,
        points
      } of this.#lines) {
        Outline._translate(line, tx, ty, line);
        Outline._translate(points, tx, ty, points);
      }
    } else {
      const sx = this.#parentWidth / newParentWidth;
      const sy = this.#parentHeight / newParentHeight;
      this.#parentWidth = newParentWidth;
      this.#parentHeight = newParentHeight;
      for (const {
        line,
        points
      } of this.#lines) {
        Outline._rescale(line, tx, ty, sx, sy, line);
        Outline._rescale(points, tx, ty, sx, sy, points);
      }
      bbox[2] *= sx;
      bbox[3] *= sy;
    }
    bbox[0] = newX;
    bbox[1] = newY;
    return {
      root: {
        viewBox: this.viewBox
      },
      path: {
        d: this.toSVGPath(),
        "transform-origin": `${Outline.svgRound(newX)} ${Outline.svgRound(newY)}`
      }
    };
  }
  get defaultSVGProperties() {
    const bbox = this.#bbox;
    return {
      root: {
        viewBox: this.viewBox
      },
      rootClass: {
        draw: true
      },
      path: {
        d: this.toSVGPath(),
        "transform-origin": `${Outline.svgRound(bbox[0])} ${Outline.svgRound(bbox[1])}`,
        transform: this.rotationTransform || null
      },
      bbox
    };
  }
}

;// ./src/display/editor/ink.js






class InkDrawingOptions extends DrawingOptions {
  constructor(viewerParameters) {
    super();
    this._viewParameters = viewerParameters;
    super.updateProperties({
      fill: "none",
      stroke: AnnotationEditor._defaultLineColor,
      "stroke-opacity": 1,
      "stroke-width": 1,
      "stroke-linecap": "round",
      "stroke-linejoin": "round",
      "stroke-miterlimit": 10
    });
  }
  updateSVGProperty(name, value) {
    if (name === "stroke-width") {
      value ??= this["stroke-width"];
      value *= this._viewParameters.realScale;
    }
    super.updateSVGProperty(name, value);
  }
  clone() {
    const clone = new InkDrawingOptions(this._viewParameters);
    clone.updateAll(this);
    return clone;
  }
}
class InkEditor extends DrawingEditor {
  static _type = "ink";
  static _editorType = AnnotationEditorType.INK;
  static _defaultDrawingOptions = null;
  constructor(params) {
    super({
      ...params,
      name: "inkEditor"
    });
    this._willKeepAspectRatio = true;
    this.defaultL10nId = "pdfjs-editor-ink-editor";
  }
  static initialize(l10n, uiManager) {
    AnnotationEditor.initialize(l10n, uiManager);
    this._defaultDrawingOptions = new InkDrawingOptions(uiManager.viewParameters);
  }
  static getDefaultDrawingOptions(options) {
    const clone = this._defaultDrawingOptions.clone();
    clone.updateProperties(options);
    return clone;
  }
  static get supportMultipleDrawings() {
    return true;
  }
  static get typesMap() {
    return shadow(this, "typesMap", new Map([[AnnotationEditorParamsType.INK_THICKNESS, "stroke-width"], [AnnotationEditorParamsType.INK_COLOR, "stroke"], [AnnotationEditorParamsType.INK_OPACITY, "stroke-opacity"]]));
  }
  static createDrawerInstance({
    x,
    y,
    box: [,, width, height],
    rotation,
    timeStamp
  }) {
    return new InkDrawOutliner(x, y, width, height, rotation, this._defaultDrawingOptions["stroke-width"], timeStamp);
  }
  static deserializeDraw(pageX, pageY, pageWidth, pageHeight, innerMargin, data) {
    return InkDrawOutline.deserialize(pageX, pageY, pageWidth, pageHeight, innerMargin, data);
  }
  static async deserialize(data, parent, uiManager) {
    let initialData = null;
    if (data instanceof InkAnnotationElement) {
      const {
        data: {
          inkLists,
          rect,
          rotation,
          id,
          color,
          opacity,
          borderStyle: {
            rawWidth: thickness
          },
          popupRef,
          richText,
          contentsObj,
          creationDate,
          modificationDate
        },
        parent: {
          page: {
            pageNumber
          }
        }
      } = data;
      initialData = data = {
        annotationType: AnnotationEditorType.INK,
        color: Array.from(color),
        thickness,
        opacity,
        paths: {
          points: inkLists
        },
        boxes: null,
        pageIndex: pageNumber - 1,
        rect: rect.slice(0),
        rotation,
        annotationElementId: id,
        id,
        deleted: false,
        popupRef,
        richText,
        comment: contentsObj?.str || null,
        creationDate,
        modificationDate
      };
    }
    const editor = await super.deserialize(data, parent, uiManager);
    editor._initialData = initialData;
    if (data.comment) {
      editor.setCommentData(data);
    }
    return editor;
  }
  get toolbarButtons() {
    this._colorPicker ||= new BasicColorPicker(this);
    return [["colorPicker", this._colorPicker]];
  }
  get colorType() {
    return AnnotationEditorParamsType.INK_COLOR;
  }
  get colorAndOpacityType() {
    return AnnotationEditorParamsType.INK_COLOR_AND_OPACITY;
  }
  get opacityType() {
    return AnnotationEditorParamsType.INK_OPACITY;
  }
  updateParams(type, value) {
    if (type === AnnotationEditorParamsType.INK_COLOR_AND_OPACITY) {
      this._updateColorAndOpacity(value.color, value.opacity);
      return;
    }
    super.updateParams(type, value);
  }
  static updateDefaultParams(type, value) {
    if (type === AnnotationEditorParamsType.INK_COLOR_AND_OPACITY) {
      super.updateDefaultParams(AnnotationEditorParamsType.INK_COLOR, value.color);
      super.updateDefaultParams(AnnotationEditorParamsType.INK_OPACITY, value.opacity);
      return;
    }
    super.updateDefaultParams(type, value);
  }
  get color() {
    return this._drawingOptions.stroke;
  }
  get opacity() {
    return this._drawingOptions["stroke-opacity"];
  }
  onScaleChanging() {
    if (!this.parent) {
      return;
    }
    super.onScaleChanging();
    const {
      _drawId,
      _drawingOptions,
      parent
    } = this;
    _drawingOptions.updateSVGProperty("stroke-width");
    parent.drawLayer.updateProperties(_drawId, _drawingOptions.toSVGProperties());
  }
  static onScaleChangingWhenDrawing() {
    const parent = this._currentParent;
    if (!parent) {
      return;
    }
    super.onScaleChangingWhenDrawing();
    this._defaultDrawingOptions.updateSVGProperty("stroke-width");
    parent.drawLayer.updateProperties(this._currentDrawId, this._defaultDrawingOptions.toSVGProperties());
  }
  createDrawingOptions({
    color,
    thickness,
    opacity
  }) {
    this._drawingOptions = InkEditor.getDefaultDrawingOptions({
      stroke: Util.makeHexColor(...color),
      "stroke-width": thickness,
      "stroke-opacity": opacity
    });
  }
  serialize(isForCopying = false) {
    if (this.isEmpty()) {
      return null;
    }
    if (this.deleted) {
      return this.serializeDeleted();
    }
    const {
      lines,
      points
    } = this.serializeDraw(isForCopying);
    const {
      _drawingOptions: {
        stroke,
        "stroke-opacity": opacity,
        "stroke-width": thickness
      }
    } = this;
    const serialized = Object.assign(super.serialize(isForCopying), {
      color: AnnotationEditor._colorManager.convert(stroke),
      opacity,
      thickness,
      paths: {
        lines,
        points
      }
    });
    this.addComment(serialized);
    if (isForCopying) {
      serialized.isCopy = true;
      return serialized;
    }
    if (this.annotationElementId && !this.#hasElementChanged(serialized)) {
      return null;
    }
    serialized.id = this.annotationElementId;
    return serialized;
  }
  #hasElementChanged(serialized) {
    const {
      color,
      thickness,
      opacity,
      pageIndex
    } = this._initialData;
    return this.hasEditedComment || this._hasBeenMoved || this._hasBeenResized || serialized.color.some((c, i) => c !== color[i]) || serialized.thickness !== thickness || serialized.opacity !== opacity || serialized.pageIndex !== pageIndex;
  }
  renderAnnotationElement(annotation) {
    if (this.deleted) {
      annotation.hide();
      return null;
    }
    const {
      points,
      rect
    } = this.serializeDraw(false);
    annotation.updateEdited({
      rect,
      thickness: this._drawingOptions["stroke-width"],
      points,
      popup: this.comment
    });
    return null;
  }
}

;// ./src/display/editor/drawers/contour.js

class ContourDrawOutline extends InkDrawOutline {
  toSVGPath() {
    let path = super.toSVGPath();
    if (!path.endsWith("Z")) {
      path += "Z";
    }
    return path;
  }
}

;// ./src/display/editor/drawers/signaturedraw.js




const BASE_HEADER_LENGTH = 8;
const POINTS_PROPERTIES_NUMBER = 3;
class SignatureExtractor {
  static #PARAMETERS = {
    maxDim: 512,
    sigmaSFactor: 0.02,
    sigmaR: 25,
    kernelSize: 16
  };
  static #neighborIndexToId(i0, j0, i, j) {
    i -= i0;
    j -= j0;
    if (i === 0) {
      return j > 0 ? 0 : 4;
    }
    return i === 1 ? j + 6 : 2 - j;
  }
  static #neighborIdToIndex = new Int32Array([0, 1, -1, 1, -1, 0, -1, -1, 0, -1, 1, -1, 1, 0, 1, 1]);
  static #clockwiseNonZero(buf, width, i0, j0, i, j, offset) {
    const id = this.#neighborIndexToId(i0, j0, i, j);
    for (let k = 0; k < 8; k++) {
      const kk = (-k + id - offset + 16) % 8;
      const shiftI = this.#neighborIdToIndex[2 * kk];
      const shiftJ = this.#neighborIdToIndex[2 * kk + 1];
      if (buf[(i0 + shiftI) * width + (j0 + shiftJ)] !== 0) {
        return kk;
      }
    }
    return -1;
  }
  static #counterClockwiseNonZero(buf, width, i0, j0, i, j, offset) {
    const id = this.#neighborIndexToId(i0, j0, i, j);
    for (let k = 0; k < 8; k++) {
      const kk = (k + id + offset + 16) % 8;
      const shiftI = this.#neighborIdToIndex[2 * kk];
      const shiftJ = this.#neighborIdToIndex[2 * kk + 1];
      if (buf[(i0 + shiftI) * width + (j0 + shiftJ)] !== 0) {
        return kk;
      }
    }
    return -1;
  }
  static #findContours(buf, width, height, threshold) {
    const N = buf.length;
    const types = new Int32Array(N);
    for (let i = 0; i < N; i++) {
      types[i] = buf[i] <= threshold ? 1 : 0;
    }
    for (let i = 1; i < height - 1; i++) {
      types[i * width] = types[i * width + width - 1] = 0;
    }
    for (let i = 0; i < width; i++) {
      types[i] = types[width * height - 1 - i] = 0;
    }
    let nbd = 1;
    let lnbd;
    const contours = [];
    for (let i = 1; i < height - 1; i++) {
      lnbd = 1;
      for (let j = 1; j < width - 1; j++) {
        const ij = i * width + j;
        const pix = types[ij];
        if (pix === 0) {
          continue;
        }
        let i2 = i;
        let j2 = j;
        if (pix === 1 && types[ij - 1] === 0) {
          nbd += 1;
          j2 -= 1;
        } else if (pix >= 1 && types[ij + 1] === 0) {
          nbd += 1;
          j2 += 1;
          if (pix > 1) {
            lnbd = pix;
          }
        } else {
          if (pix !== 1) {
            lnbd = Math.abs(pix);
          }
          continue;
        }
        const points = [j, i];
        const isHole = j2 === j + 1;
        const contour = {
          isHole,
          points,
          id: nbd,
          parent: 0
        };
        contours.push(contour);
        let contour0;
        for (const c of contours) {
          if (c.id === lnbd) {
            contour0 = c;
            break;
          }
        }
        if (!contour0) {
          contour.parent = isHole ? lnbd : 0;
        } else if (contour0.isHole) {
          contour.parent = isHole ? contour0.parent : lnbd;
        } else {
          contour.parent = isHole ? lnbd : contour0.parent;
        }
        const k = this.#clockwiseNonZero(types, width, i, j, i2, j2, 0);
        if (k === -1) {
          types[ij] = -nbd;
          if (types[ij] !== 1) {
            lnbd = Math.abs(types[ij]);
          }
          continue;
        }
        let shiftI = this.#neighborIdToIndex[2 * k];
        let shiftJ = this.#neighborIdToIndex[2 * k + 1];
        const i1 = i + shiftI;
        const j1 = j + shiftJ;
        i2 = i1;
        j2 = j1;
        let i3 = i;
        let j3 = j;
        while (true) {
          const kk = this.#counterClockwiseNonZero(types, width, i3, j3, i2, j2, 1);
          shiftI = this.#neighborIdToIndex[2 * kk];
          shiftJ = this.#neighborIdToIndex[2 * kk + 1];
          const i4 = i3 + shiftI;
          const j4 = j3 + shiftJ;
          points.push(j4, i4);
          const ij3 = i3 * width + j3;
          if (types[ij3 + 1] === 0) {
            types[ij3] = -nbd;
          } else if (types[ij3] === 1) {
            types[ij3] = nbd;
          }
          if (i4 === i && j4 === j && i3 === i1 && j3 === j1) {
            if (types[ij] !== 1) {
              lnbd = Math.abs(types[ij]);
            }
            break;
          } else {
            i2 = i3;
            j2 = j3;
            i3 = i4;
            j3 = j4;
          }
        }
      }
    }
    return contours;
  }
  static #douglasPeuckerHelper(points, start, end, output) {
    if (end - start <= 4) {
      for (let i = start; i < end - 2; i += 2) {
        output.push(points[i], points[i + 1]);
      }
      return;
    }
    const ax = points[start];
    const ay = points[start + 1];
    const abx = points[end - 4] - ax;
    const aby = points[end - 3] - ay;
    const dist = Math.hypot(abx, aby);
    const nabx = abx / dist;
    const naby = aby / dist;
    const aa = nabx * ay - naby * ax;
    const m = aby / abx;
    const invS = 1 / dist;
    const phi = Math.atan(m);
    const cosPhi = Math.cos(phi);
    const sinPhi = Math.sin(phi);
    const tmax = invS * (Math.abs(cosPhi) + Math.abs(sinPhi));
    const poly = invS * (1 - tmax + tmax ** 2);
    const partialPhi = Math.max(Math.atan(Math.abs(sinPhi + cosPhi) * poly), Math.atan(Math.abs(sinPhi - cosPhi) * poly));
    let dmax = 0;
    let index = start;
    for (let i = start + 2; i < end - 2; i += 2) {
      const d = Math.abs(aa - nabx * points[i + 1] + naby * points[i]);
      if (d > dmax) {
        index = i;
        dmax = d;
      }
    }
    if (dmax > (dist * partialPhi) ** 2) {
      this.#douglasPeuckerHelper(points, start, index + 2, output);
      this.#douglasPeuckerHelper(points, index, end, output);
    } else {
      output.push(ax, ay);
    }
  }
  static #douglasPeucker(points) {
    const output = [];
    const len = points.length;
    this.#douglasPeuckerHelper(points, 0, len, output);
    output.push(points[len - 2], points[len - 1]);
    return output.length <= 4 ? null : output;
  }
  static #bilateralFilter(buf, width, height, sigmaS, sigmaR, kernelSize) {
    const kernel = new Float32Array(kernelSize ** 2);
    const sigmaS2 = -2 * sigmaS ** 2;
    const halfSize = kernelSize >> 1;
    for (let i = 0; i < kernelSize; i++) {
      const x = (i - halfSize) ** 2;
      for (let j = 0; j < kernelSize; j++) {
        kernel[i * kernelSize + j] = Math.exp((x + (j - halfSize) ** 2) / sigmaS2);
      }
    }
    const rangeValues = new Float32Array(256);
    const sigmaR2 = -2 * sigmaR ** 2;
    for (let i = 0; i < 256; i++) {
      rangeValues[i] = Math.exp(i ** 2 / sigmaR2);
    }
    const N = buf.length;
    const out = new Uint8Array(N);
    const histogram = new Uint32Array(256);
    for (let i = 0; i < height; i++) {
      for (let j = 0; j < width; j++) {
        const ij = i * width + j;
        const center = buf[ij];
        let sum = 0;
        let norm = 0;
        for (let k = 0; k < kernelSize; k++) {
          const y = i + k - halfSize;
          if (y < 0 || y >= height) {
            continue;
          }
          for (let l = 0; l < kernelSize; l++) {
            const x = j + l - halfSize;
            if (x < 0 || x >= width) {
              continue;
            }
            const neighbour = buf[y * width + x];
            const w = kernel[k * kernelSize + l] * rangeValues[Math.abs(neighbour - center)];
            sum += neighbour * w;
            norm += w;
          }
        }
        const pix = out[ij] = Math.round(sum / norm);
        histogram[pix]++;
      }
    }
    return [out, histogram];
  }
  static #getHistogram(buf) {
    const histogram = new Uint32Array(256);
    for (const g of buf) {
      histogram[g]++;
    }
    return histogram;
  }
  static #toUint8(buf) {
    const N = buf.length;
    const out = new Uint8ClampedArray(N >> 2);
    let max = -Infinity;
    let min = Infinity;
    for (let i = 0, ii = out.length; i < ii; i++) {
      const pix = out[i] = buf[i << 2];
      max = Math.max(max, pix);
      min = Math.min(min, pix);
    }
    const ratio = 255 / (max - min);
    for (let i = 0, ii = out.length; i < ii; i++) {
      out[i] = (out[i] - min) * ratio;
    }
    return out;
  }
  static #guessThreshold(histogram) {
    let i;
    let M = -Infinity;
    let L = -Infinity;
    const min = histogram.findIndex(v => v !== 0);
    let pos = min;
    let spos = min;
    for (i = min; i < 256; i++) {
      const v = histogram[i];
      if (v > M) {
        if (i - pos > L) {
          L = i - pos;
          spos = i - 1;
        }
        M = v;
        pos = i;
      }
    }
    for (i = spos - 1; i >= 0; i--) {
      if (histogram[i] > histogram[i + 1]) {
        break;
      }
    }
    return i;
  }
  static #getGrayPixels(bitmap) {
    const originalBitmap = bitmap;
    const {
      width,
      height
    } = bitmap;
    const {
      maxDim
    } = this.#PARAMETERS;
    let newWidth = width;
    let newHeight = height;
    if (width > maxDim || height > maxDim) {
      let prevWidth = width;
      let prevHeight = height;
      let steps = Math.log2(Math.max(width, height) / maxDim);
      const isteps = Math.floor(steps);
      steps = steps === isteps ? isteps - 1 : isteps;
      for (let i = 0; i < steps; i++) {
        newWidth = Math.ceil(prevWidth / 2);
        newHeight = Math.ceil(prevHeight / 2);
        const offscreen = new OffscreenCanvas(newWidth, newHeight);
        const ctx = offscreen.getContext("2d");
        ctx.drawImage(bitmap, 0, 0, prevWidth, prevHeight, 0, 0, newWidth, newHeight);
        prevWidth = newWidth;
        prevHeight = newHeight;
        if (bitmap !== originalBitmap) {
          bitmap.close();
        }
        bitmap = offscreen.transferToImageBitmap();
      }
      const ratio = Math.min(maxDim / newWidth, maxDim / newHeight);
      newWidth = Math.round(newWidth * ratio);
      newHeight = Math.round(newHeight * ratio);
    }
    const offscreen = new OffscreenCanvas(newWidth, newHeight);
    const ctx = offscreen.getContext("2d", {
      willReadFrequently: true
    });
    ctx.fillStyle = "white";
    ctx.fillRect(0, 0, newWidth, newHeight);
    ctx.filter = "grayscale(1)";
    ctx.drawImage(bitmap, 0, 0, bitmap.width, bitmap.height, 0, 0, newWidth, newHeight);
    const grayImage = ctx.getImageData(0, 0, newWidth, newHeight).data;
    const uint8Buf = this.#toUint8(grayImage);
    return [uint8Buf, newWidth, newHeight];
  }
  static extractContoursFromText(text, {
    fontFamily,
    fontStyle,
    fontWeight
  }, pageWidth, pageHeight, rotation, innerMargin) {
    let canvas = new OffscreenCanvas(1, 1);
    let ctx = canvas.getContext("2d", {
      alpha: false
    });
    const fontSize = 200;
    const font = ctx.font = `${fontStyle} ${fontWeight} ${fontSize}px ${fontFamily}`;
    const {
      actualBoundingBoxLeft,
      actualBoundingBoxRight,
      actualBoundingBoxAscent,
      actualBoundingBoxDescent,
      fontBoundingBoxAscent,
      fontBoundingBoxDescent,
      width
    } = ctx.measureText(text);
    const SCALE = 1.5;
    const canvasWidth = Math.ceil(Math.max(Math.abs(actualBoundingBoxLeft) + Math.abs(actualBoundingBoxRight) || 0, width) * SCALE);
    const canvasHeight = Math.ceil(Math.max(Math.abs(actualBoundingBoxAscent) + Math.abs(actualBoundingBoxDescent) || fontSize, Math.abs(fontBoundingBoxAscent) + Math.abs(fontBoundingBoxDescent) || fontSize) * SCALE);
    canvas = new OffscreenCanvas(canvasWidth, canvasHeight);
    ctx = canvas.getContext("2d", {
      alpha: true,
      willReadFrequently: true
    });
    ctx.font = font;
    ctx.filter = "grayscale(1)";
    ctx.fillStyle = "white";
    ctx.fillRect(0, 0, canvasWidth, canvasHeight);
    ctx.fillStyle = "black";
    ctx.fillText(text, canvasWidth * (SCALE - 1) / 2, canvasHeight * (3 - SCALE) / 2);
    const uint8Buf = this.#toUint8(ctx.getImageData(0, 0, canvasWidth, canvasHeight).data);
    const histogram = this.#getHistogram(uint8Buf);
    const threshold = this.#guessThreshold(histogram);
    const contourList = this.#findContours(uint8Buf, canvasWidth, canvasHeight, threshold);
    return this.processDrawnLines({
      lines: {
        curves: contourList,
        width: canvasWidth,
        height: canvasHeight
      },
      pageWidth,
      pageHeight,
      rotation,
      innerMargin,
      mustSmooth: true,
      areContours: true
    });
  }
  static process(bitmap, pageWidth, pageHeight, rotation, innerMargin) {
    const [uint8Buf, width, height] = this.#getGrayPixels(bitmap);
    const [buffer, histogram] = this.#bilateralFilter(uint8Buf, width, height, Math.hypot(width, height) * this.#PARAMETERS.sigmaSFactor, this.#PARAMETERS.sigmaR, this.#PARAMETERS.kernelSize);
    const threshold = this.#guessThreshold(histogram);
    const contourList = this.#findContours(buffer, width, height, threshold);
    return this.processDrawnLines({
      lines: {
        curves: contourList,
        width,
        height
      },
      pageWidth,
      pageHeight,
      rotation,
      innerMargin,
      mustSmooth: true,
      areContours: true
    });
  }
  static processDrawnLines({
    lines,
    pageWidth,
    pageHeight,
    rotation,
    innerMargin,
    mustSmooth,
    areContours
  }) {
    if (rotation % 180 !== 0) {
      [pageWidth, pageHeight] = [pageHeight, pageWidth];
    }
    const {
      curves,
      width,
      height
    } = lines;
    const thickness = lines.thickness ?? 0;
    const linesAndPoints = [];
    const ratio = Math.min(pageWidth / width, pageHeight / height);
    const xScale = ratio / pageWidth;
    const yScale = ratio / pageHeight;
    const newCurves = [];
    for (const {
      points
    } of curves) {
      const reducedPoints = mustSmooth ? this.#douglasPeucker(points) : points;
      if (!reducedPoints) {
        continue;
      }
      newCurves.push(reducedPoints);
      const len = reducedPoints.length;
      const newPoints = new Float32Array(len);
      const line = new Float32Array(3 * (len === 2 ? 2 : len - 2));
      linesAndPoints.push({
        line,
        points: newPoints
      });
      if (len === 2) {
        newPoints[0] = reducedPoints[0] * xScale;
        newPoints[1] = reducedPoints[1] * yScale;
        line.set([NaN, NaN, NaN, NaN, newPoints[0], newPoints[1]], 0);
        continue;
      }
      let [x1, y1, x2, y2] = reducedPoints;
      x1 *= xScale;
      y1 *= yScale;
      x2 *= xScale;
      y2 *= yScale;
      newPoints.set([x1, y1, x2, y2], 0);
      line.set([NaN, NaN, NaN, NaN, x1, y1], 0);
      for (let i = 4; i < len; i += 2) {
        const x = newPoints[i] = reducedPoints[i] * xScale;
        const y = newPoints[i + 1] = reducedPoints[i + 1] * yScale;
        line.set(Outline.createBezierPoints(x1, y1, x2, y2, x, y), (i - 2) * 3);
        [x1, y1, x2, y2] = [x2, y2, x, y];
      }
    }
    if (linesAndPoints.length === 0) {
      return null;
    }
    const outline = areContours ? new ContourDrawOutline() : new InkDrawOutline();
    outline.build(linesAndPoints, pageWidth, pageHeight, 1, rotation, areContours ? 0 : thickness, innerMargin);
    return {
      outline,
      newCurves,
      areContours,
      thickness,
      width,
      height
    };
  }
  static async compressSignature({
    outlines,
    areContours,
    thickness,
    width,
    height
  }) {
    let minDiff = Infinity;
    let maxDiff = -Infinity;
    let outlinesLength = 0;
    for (const points of outlines) {
      outlinesLength += points.length;
      for (let i = 2, ii = points.length; i < ii; i++) {
        const dx = points[i] - points[i - 2];
        minDiff = Math.min(minDiff, dx);
        maxDiff = Math.max(maxDiff, dx);
      }
    }
    let bufferType;
    if (minDiff >= -128 && maxDiff <= 127) {
      bufferType = Int8Array;
    } else if (minDiff >= -32768 && maxDiff <= 32767) {
      bufferType = Int16Array;
    } else {
      bufferType = Int32Array;
    }
    const len = outlines.length;
    const headerLength = BASE_HEADER_LENGTH + POINTS_PROPERTIES_NUMBER * len;
    const header = new Uint32Array(headerLength);
    let offset = 0;
    header[offset++] = headerLength * Uint32Array.BYTES_PER_ELEMENT + (outlinesLength - 2 * len) * bufferType.BYTES_PER_ELEMENT;
    header[offset++] = 0;
    header[offset++] = width;
    header[offset++] = height;
    header[offset++] = areContours ? 0 : 1;
    header[offset++] = Math.max(0, Math.floor(thickness ?? 0));
    header[offset++] = len;
    header[offset++] = bufferType.BYTES_PER_ELEMENT;
    for (const points of outlines) {
      header[offset++] = points.length - 2;
      header[offset++] = points[0];
      header[offset++] = points[1];
    }
    const cs = new CompressionStream("deflate-raw");
    const writer = cs.writable.getWriter();
    await writer.ready;
    writer.write(header);
    const BufferCtor = bufferType.prototype.constructor;
    for (const points of outlines) {
      const diffs = new BufferCtor(points.length - 2);
      for (let i = 2, ii = points.length; i < ii; i++) {
        diffs[i - 2] = points[i] - points[i - 2];
      }
      writer.write(diffs);
    }
    writer.close();
    const bytes = await new Response(cs.readable).bytes();
    return bytes.toBase64();
  }
  static async decompressSignature(signatureData) {
    try {
      const bytes = Uint8Array.fromBase64(signatureData);
      const {
        readable,
        writable
      } = new DecompressionStream("deflate-raw");
      const writer = writable.getWriter();
      await writer.ready;
      writer.write(bytes).then(async () => {
        await writer.ready;
        await writer.close();
      }).catch(() => {});
      let data = null;
      let offset = 0;
      for await (const chunk of readable) {
        data ||= new Uint8Array(new Uint32Array(chunk.buffer, 0, 4)[0]);
        data.set(chunk, offset);
        offset += chunk.length;
      }
      const header = new Uint32Array(data.buffer, 0, data.length >> 2);
      const version = header[1];
      if (version !== 0) {
        throw new Error(`Invalid version: ${version}`);
      }
      const width = header[2];
      const height = header[3];
      const areContours = header[4] === 0;
      const thickness = header[5];
      const numberOfDrawings = header[6];
      const bufferType = header[7];
      const outlines = [];
      const diffsOffset = (BASE_HEADER_LENGTH + POINTS_PROPERTIES_NUMBER * numberOfDrawings) * Uint32Array.BYTES_PER_ELEMENT;
      let diffs;
      switch (bufferType) {
        case Int8Array.BYTES_PER_ELEMENT:
          diffs = new Int8Array(data.buffer, diffsOffset);
          break;
        case Int16Array.BYTES_PER_ELEMENT:
          diffs = new Int16Array(data.buffer, diffsOffset);
          break;
        case Int32Array.BYTES_PER_ELEMENT:
          diffs = new Int32Array(data.buffer, diffsOffset);
          break;
      }
      offset = 0;
      for (let i = 0; i < numberOfDrawings; i++) {
        const len = header[POINTS_PROPERTIES_NUMBER * i + BASE_HEADER_LENGTH];
        const points = new Float32Array(len + 2);
        outlines.push(points);
        for (let j = 0; j < POINTS_PROPERTIES_NUMBER - 1; j++) {
          points[j] = header[POINTS_PROPERTIES_NUMBER * i + BASE_HEADER_LENGTH + j + 1];
        }
        for (let j = 0; j < len; j++) {
          points[j + 2] = points[j] + diffs[offset++];
        }
      }
      return {
        areContours,
        thickness,
        outlines,
        width,
        height
      };
    } catch (e) {
      warn(`decompressSignature: ${e}`);
      return null;
    }
  }
}

;// ./src/display/editor/signature.js







class SignatureOptions extends DrawingOptions {
  constructor() {
    super();
    super.updateProperties({
      fill: AnnotationEditor._defaultLineColor,
      "stroke-width": 0
    });
  }
  clone() {
    const clone = new SignatureOptions();
    clone.updateAll(this);
    return clone;
  }
}
class DrawnSignatureOptions extends InkDrawingOptions {
  constructor(viewerParameters) {
    super(viewerParameters);
    super.updateProperties({
      stroke: AnnotationEditor._defaultLineColor,
      "stroke-width": 1
    });
  }
  clone() {
    const clone = new DrawnSignatureOptions(this._viewParameters);
    clone.updateAll(this);
    return clone;
  }
}
class SignatureEditor extends DrawingEditor {
  #isExtracted = false;
  #description = null;
  #signatureData = null;
  #signatureUUID = null;
  #isWaitingForSignature = false;
  static _type = "signature";
  static _editorType = AnnotationEditorType.SIGNATURE;
  static _defaultDrawingOptions = null;
  constructor(params) {
    super({
      ...params,
      mustBeCommitted: true,
      name: "signatureEditor"
    });
    this._willKeepAspectRatio = true;
    this.#signatureData = params.signatureData || null;
    this.#description = null;
    this.defaultL10nId = "pdfjs-editor-signature-editor1";
  }
  static initialize(l10n, uiManager) {
    AnnotationEditor.initialize(l10n, uiManager);
    this._defaultDrawingOptions = new SignatureOptions();
    this._defaultDrawnSignatureOptions = new DrawnSignatureOptions(uiManager.viewParameters);
  }
  static getDefaultDrawingOptions(options) {
    const clone = this._defaultDrawingOptions.clone();
    clone.updateProperties(options);
    return clone;
  }
  static get supportMultipleDrawings() {
    return false;
  }
  static get typesMap() {
    return shadow(this, "typesMap", new Map());
  }
  static get isDrawer() {
    return false;
  }
  get telemetryFinalData() {
    return {
      type: "signature",
      hasDescription: !!this.#description
    };
  }
  static computeTelemetryFinalData(data) {
    const hasDescriptionStats = data.get("hasDescription");
    return {
      hasAltText: hasDescriptionStats.get(true) ?? 0,
      hasNoAltText: hasDescriptionStats.get(false) ?? 0
    };
  }
  get isResizable() {
    return true;
  }
  onceAdded(focus) {
    this.#isWaitingForSignature = this._drawId === null;
    super.onceAdded(focus);
  }
  onScaleChanging() {
    if (this._drawId === null) {
      return;
    }
    super.onScaleChanging();
  }
  render() {
    if (this.div) {
      return this.div;
    }
    let baseX, baseY;
    const {
      _isCopy
    } = this;
    if (_isCopy) {
      this._isCopy = false;
      baseX = this.x;
      baseY = this.y;
    }
    super.render();
    if (this._drawId === null) {
      if (this.#signatureData) {
        const {
          lines,
          mustSmooth,
          areContours,
          description,
          uuid,
          heightInPage
        } = this.#signatureData;
        const {
          rawDims: {
            pageWidth,
            pageHeight
          },
          rotation
        } = this.parent.viewport;
        const outline = SignatureExtractor.processDrawnLines({
          lines,
          pageWidth,
          pageHeight,
          rotation,
          innerMargin: SignatureEditor._INNER_MARGIN,
          mustSmooth,
          areContours
        });
        this.addSignature(outline, heightInPage, description, uuid);
      } else {
        this.div.setAttribute("data-l10n-args", JSON.stringify({
          description: ""
        }));
        this.div.hidden = true;
        this._uiManager.getSignature(this);
      }
    } else {
      this.div.setAttribute("data-l10n-args", JSON.stringify({
        description: this.#description || ""
      }));
    }
    if (_isCopy) {
      this._isCopy = true;
      this._moveAfterPaste(baseX, baseY);
    }
    return this.div;
  }
  setUuid(uuid) {
    this.#signatureUUID = uuid;
    this.addEditToolbar();
  }
  getUuid() {
    return this.#signatureUUID;
  }
  get description() {
    return this.#description;
  }
  set description(description) {
    this.#description = description;
    if (!this.div) {
      return;
    }
    this.div.setAttribute("data-l10n-args", JSON.stringify({
      description
    }));
    super.addEditToolbar().then(toolbar => {
      toolbar?.updateEditSignatureButton(description);
    });
  }
  getSignaturePreview() {
    const {
      newCurves,
      areContours,
      thickness,
      width,
      height
    } = this.#signatureData;
    const maxDim = Math.max(width, height);
    const outlineData = SignatureExtractor.processDrawnLines({
      lines: {
        curves: newCurves.map(points => ({
          points
        })),
        thickness,
        width,
        height
      },
      pageWidth: maxDim,
      pageHeight: maxDim,
      rotation: 0,
      innerMargin: 0,
      mustSmooth: false,
      areContours
    });
    return {
      areContours,
      outline: outlineData.outline
    };
  }
  get toolbarButtons() {
    return this._uiManager.signatureManager ? [["editSignature", this._uiManager.signatureManager]] : super.toolbarButtons;
  }
  addSignature(data, heightInPage, description, uuid) {
    const {
      x: savedX,
      y: savedY
    } = this;
    const {
      outline
    } = this.#signatureData = data;
    this.#isExtracted = outline instanceof ContourDrawOutline;
    this.description = description;
    let drawingOptions;
    if (this.#isExtracted) {
      drawingOptions = SignatureEditor.getDefaultDrawingOptions();
    } else {
      drawingOptions = SignatureEditor._defaultDrawnSignatureOptions.clone();
      drawingOptions.updateProperties({
        "stroke-width": outline.thickness
      });
    }
    this._addOutlines({
      drawOutlines: outline,
      drawingOptions
    });
    const [, pageHeight] = this.pageDimensions;
    let newHeight = heightInPage / pageHeight;
    newHeight = newHeight >= 1 ? 0.5 : newHeight;
    this.width *= newHeight / this.height;
    if (this.width >= 1) {
      newHeight *= 0.9 / this.width;
      this.width = 0.9;
    }
    this.height = newHeight;
    this.setDims();
    this.x = savedX;
    this.y = savedY;
    this.center();
    this._onResized();
    this.onScaleChanging();
    this.rotate();
    this._uiManager.addToAnnotationStorage(this);
    this.setUuid(uuid);
    this._reportTelemetry({
      action: "pdfjs.signature.inserted",
      data: {
        hasBeenSaved: !!uuid,
        hasDescription: !!description
      }
    });
    this.div.hidden = false;
    if (this.#isWaitingForSignature) {
      this.#isWaitingForSignature = false;
      this.parent.addUndoableEditor(this);
    }
  }
  getFromImage(bitmap) {
    const {
      rawDims: {
        pageWidth,
        pageHeight
      },
      rotation
    } = this.parent.viewport;
    return SignatureExtractor.process(bitmap, pageWidth, pageHeight, rotation, SignatureEditor._INNER_MARGIN);
  }
  getFromText(text, fontInfo) {
    const {
      rawDims: {
        pageWidth,
        pageHeight
      },
      rotation
    } = this.parent.viewport;
    return SignatureExtractor.extractContoursFromText(text, fontInfo, pageWidth, pageHeight, rotation, SignatureEditor._INNER_MARGIN);
  }
  getDrawnSignature(curves) {
    const {
      rawDims: {
        pageWidth,
        pageHeight
      },
      rotation
    } = this.parent.viewport;
    return SignatureExtractor.processDrawnLines({
      lines: curves,
      pageWidth,
      pageHeight,
      rotation,
      innerMargin: SignatureEditor._INNER_MARGIN,
      mustSmooth: false,
      areContours: false
    });
  }
  createDrawingOptions({
    areContours,
    thickness
  }) {
    if (areContours) {
      this._drawingOptions = SignatureEditor.getDefaultDrawingOptions();
    } else {
      this._drawingOptions = SignatureEditor._defaultDrawnSignatureOptions.clone();
      this._drawingOptions.updateProperties({
        "stroke-width": thickness
      });
    }
  }
  serialize(isForCopying = false) {
    if (this.isEmpty()) {
      return null;
    }
    const {
      lines,
      points
    } = this.serializeDraw(isForCopying);
    const {
      _drawingOptions: {
        "stroke-width": thickness
      }
    } = this;
    const serialized = Object.assign(super.serialize(isForCopying), {
      isSignature: true,
      areContours: this.#isExtracted,
      color: [0, 0, 0],
      thickness: this.#isExtracted ? 0 : thickness
    });
    this.addComment(serialized);
    if (isForCopying) {
      serialized.paths = {
        lines,
        points
      };
      serialized.uuid = this.#signatureUUID;
      serialized.isCopy = true;
    } else {
      serialized.lines = lines;
    }
    if (this.#description) {
      serialized.accessibilityData = {
        type: "Figure",
        alt: this.#description
      };
    }
    return serialized;
  }
  static deserializeDraw(pageX, pageY, pageWidth, pageHeight, innerMargin, data) {
    if (data.areContours) {
      return ContourDrawOutline.deserialize(pageX, pageY, pageWidth, pageHeight, innerMargin, data);
    }
    return InkDrawOutline.deserialize(pageX, pageY, pageWidth, pageHeight, innerMargin, data);
  }
  static async deserialize(data, parent, uiManager) {
    const editor = await super.deserialize(data, parent, uiManager);
    editor.#isExtracted = data.areContours;
    editor.description = data.accessibilityData?.alt || "";
    editor.#signatureUUID = data.uuid;
    return editor;
  }
}

;// ./src/display/editor/stamp.js





class StampEditor extends AnnotationEditor {
  #bitmap = null;
  #bitmapId = null;
  #bitmapPromise = null;
  #bitmapUrl = null;
  #bitmapFile = null;
  #bitmapFileName = "";
  #canvas = null;
  #missingCanvas = false;
  #resizeTimeoutId = null;
  #isSvg = false;
  #hasBeenAddedInUndoStack = false;
  static _type = "stamp";
  static _editorType = AnnotationEditorType.STAMP;
  constructor(params) {
    super({
      ...params,
      name: "stampEditor"
    });
    this.#bitmapUrl = params.bitmapUrl;
    this.#bitmapFile = params.bitmapFile;
    this.defaultL10nId = "pdfjs-editor-stamp-editor";
  }
  static initialize(l10n, uiManager) {
    AnnotationEditor.initialize(l10n, uiManager);
  }
  static isHandlingMimeForPasting(mime) {
    return SupportedImageMimeTypes.has(mime);
  }
  static paste(item, parent) {
    parent.pasteEditor({
      mode: AnnotationEditorType.STAMP
    }, {
      bitmapFile: item.getAsFile()
    });
  }
  altTextFinish() {
    if (this._uiManager.useNewAltTextFlow) {
      this.div.hidden = false;
    }
    super.altTextFinish();
  }
  get telemetryFinalData() {
    return {
      type: "stamp",
      hasAltText: !!this.altTextData?.altText
    };
  }
  static computeTelemetryFinalData(data) {
    const hasAltTextStats = data.get("hasAltText");
    return {
      hasAltText: hasAltTextStats.get(true) ?? 0,
      hasNoAltText: hasAltTextStats.get(false) ?? 0
    };
  }
  #getBitmapFetched(data, fromId = false) {
    if (!data) {
      this.remove();
      return;
    }
    this.#bitmap = data.bitmap;
    if (!fromId) {
      this.#bitmapId = data.id;
      this.#isSvg = data.isSvg;
    }
    if (data.file) {
      this.#bitmapFileName = data.file.name;
    }
    this.#createCanvas();
  }
  #getBitmapDone() {
    this.#bitmapPromise = null;
    this._uiManager.enableWaiting(false);
    if (!this.#canvas) {
      return;
    }
    if (this._uiManager.useNewAltTextWhenAddingImage && this._uiManager.useNewAltTextFlow && this.#bitmap) {
      this.addEditToolbar().then(() => {
        this._editToolbar.hide();
        this._uiManager.editAltText(this, true);
      });
      return;
    }
    if (!this._uiManager.useNewAltTextWhenAddingImage && this._uiManager.useNewAltTextFlow && this.#bitmap) {
      this._reportTelemetry({
        action: "pdfjs.image.image_added",
        data: {
          alt_text_modal: false,
          alt_text_type: "empty"
        }
      });
      try {
        this.mlGuessAltText();
      } catch {}
    }
    this.div.focus();
  }
  async mlGuessAltText(imageData = null, updateAltTextData = true) {
    if (this.hasAltTextData()) {
      return null;
    }
    const {
      mlManager
    } = this._uiManager;
    if (!mlManager) {
      throw new Error("No ML.");
    }
    if (!(await mlManager.isEnabledFor("altText"))) {
      throw new Error("ML isn't enabled for alt text.");
    }
    const {
      data,
      width,
      height
    } = imageData || this.copyCanvas(null, null, true).imageData;
    const response = await mlManager.guess({
      name: "altText",
      request: {
        data,
        width,
        height,
        channels: data.length / (width * height)
      }
    });
    if (!response) {
      throw new Error("No response from the AI service.");
    }
    if (response.error) {
      throw new Error("Error from the AI service.");
    }
    if (response.cancel) {
      return null;
    }
    if (!response.output) {
      throw new Error("No valid response from the AI service.");
    }
    const altText = response.output;
    await this.setGuessedAltText(altText);
    if (updateAltTextData && !this.hasAltTextData()) {
      this.altTextData = {
        alt: altText,
        decorative: false
      };
    }
    return altText;
  }
  #getBitmap() {
    if (this.#bitmapId) {
      this._uiManager.enableWaiting(true);
      this._uiManager.imageManager.getFromId(this.#bitmapId).then(data => this.#getBitmapFetched(data, true)).finally(() => this.#getBitmapDone());
      return;
    }
    if (this.#bitmapUrl) {
      const url = this.#bitmapUrl;
      this.#bitmapUrl = null;
      this._uiManager.enableWaiting(true);
      this.#bitmapPromise = this._uiManager.imageManager.getFromUrl(url).then(data => this.#getBitmapFetched(data)).finally(() => this.#getBitmapDone());
      return;
    }
    if (this.#bitmapFile) {
      const file = this.#bitmapFile;
      this.#bitmapFile = null;
      this._uiManager.enableWaiting(true);
      this.#bitmapPromise = this._uiManager.imageManager.getFromFile(file).then(data => this.#getBitmapFetched(data)).finally(() => this.#getBitmapDone());
      return;
    }
    const input = document.createElement("input");
    input.type = "file";
    input.accept = SupportedImageMimeTypes.keys().join(",");
    const signal = this._uiManager._signal;
    this.#bitmapPromise = new Promise(resolve => {
      input.addEventListener("change", async () => {
        if (!input.files || input.files.length === 0) {
          this.remove();
        } else {
          this._uiManager.enableWaiting(true);
          const data = await this._uiManager.imageManager.getFromFile(input.files[0]);
          this._reportTelemetry({
            action: "pdfjs.image.image_selected",
            data: {
              alt_text_modal: this._uiManager.useNewAltTextFlow
            }
          });
          this.#getBitmapFetched(data);
        }
        resolve();
      }, {
        signal
      });
      input.addEventListener("cancel", () => {
        this.remove();
        resolve();
      }, {
        signal
      });
    }).finally(() => this.#getBitmapDone());
    input.click();
  }
  remove() {
    if (this.#bitmapId) {
      this.#bitmap = null;
      this._uiManager.imageManager.deleteId(this.#bitmapId);
      this.#canvas?.remove();
      this.#canvas = null;
      if (this.#resizeTimeoutId) {
        clearTimeout(this.#resizeTimeoutId);
        this.#resizeTimeoutId = null;
      }
    }
    super.remove();
  }
  rebuild() {
    if (!this.parent) {
      if (this.#bitmapId) {
        this.#getBitmap();
      }
      return;
    }
    super.rebuild();
    if (this.div === null) {
      return;
    }
    if (this.#bitmapId && this.#canvas === null) {
      this.#getBitmap();
    }
    if (!this.isAttachedToDOM) {
      this.parent.add(this);
    }
  }
  onceAdded(focus) {
    this._isDraggable = true;
    if (focus) {
      this.div.focus();
    }
  }
  isEmpty() {
    return !(this.#bitmapPromise || this.#bitmap || this.#bitmapUrl || this.#bitmapFile || this.#bitmapId || this.#missingCanvas);
  }
  get toolbarButtons() {
    return [["altText", this.createAltText()]];
  }
  get isResizable() {
    return true;
  }
  render() {
    if (this.div) {
      return this.div;
    }
    let baseX, baseY;
    if (this._isCopy) {
      baseX = this.x;
      baseY = this.y;
    }
    super.render();
    this.div.hidden = true;
    this.createAltText();
    if (!this.#missingCanvas) {
      if (this.#bitmap) {
        this.#createCanvas();
      } else {
        this.#getBitmap();
      }
    }
    if (this._isCopy) {
      this._moveAfterPaste(baseX, baseY);
    }
    this._uiManager.addShouldRescale(this);
    return this.div;
  }
  setCanvas(annotationElementId, canvas) {
    const {
      id: bitmapId,
      bitmap
    } = this._uiManager.imageManager.getFromCanvas(annotationElementId, canvas);
    canvas.remove();
    if (bitmapId && this._uiManager.imageManager.isValidId(bitmapId)) {
      this.#bitmapId = bitmapId;
      if (bitmap) {
        this.#bitmap = bitmap;
      }
      this.#missingCanvas = false;
      this.#createCanvas();
    }
  }
  _onResized() {
    this.onScaleChanging();
  }
  onScaleChanging() {
    if (!this.parent) {
      return;
    }
    if (this.#resizeTimeoutId !== null) {
      clearTimeout(this.#resizeTimeoutId);
    }
    const TIME_TO_WAIT = 200;
    this.#resizeTimeoutId = setTimeout(() => {
      this.#resizeTimeoutId = null;
      this.#drawBitmap();
    }, TIME_TO_WAIT);
  }
  #createCanvas() {
    const {
      div
    } = this;
    let {
      width,
      height
    } = this.#bitmap;
    const [pageWidth, pageHeight] = this.pageDimensions;
    const MAX_RATIO = 0.75;
    if (this.width) {
      width = this.width * pageWidth;
      height = this.height * pageHeight;
    } else if (width > MAX_RATIO * pageWidth || height > MAX_RATIO * pageHeight) {
      const factor = Math.min(MAX_RATIO * pageWidth / width, MAX_RATIO * pageHeight / height);
      width *= factor;
      height *= factor;
    }
    this._uiManager.enableWaiting(false);
    const canvas = this.#canvas = document.createElement("canvas");
    canvas.setAttribute("role", "img");
    this.addContainer(canvas);
    this.width = width / pageWidth;
    this.height = height / pageHeight;
    this.setDims();
    if (this._initialOptions?.isCentered) {
      this.center();
    } else {
      this.fixAndSetPosition();
    }
    this._initialOptions = null;
    if (!this._uiManager.useNewAltTextWhenAddingImage || !this._uiManager.useNewAltTextFlow || this.annotationElementId) {
      div.hidden = false;
    }
    this.#drawBitmap();
    if (!this.#hasBeenAddedInUndoStack) {
      this.parent.addUndoableEditor(this);
      this.#hasBeenAddedInUndoStack = true;
    }
    this._reportTelemetry({
      action: "inserted_image"
    });
    if (this.#bitmapFileName) {
      this.div.setAttribute("aria-description", this.#bitmapFileName);
    }
    if (!this.annotationElementId) {
      this._uiManager.a11yAlert(AnnotationEditor._l10nAlert.stamp);
    }
  }
  copyCanvas(maxDataDimension, maxPreviewDimension, createImageData = false) {
    maxDataDimension ||= 224;
    const {
      width: bitmapWidth,
      height: bitmapHeight
    } = this.#bitmap;
    const outputScale = new OutputScale();
    let bitmap = this.#bitmap;
    let width = bitmapWidth,
      height = bitmapHeight;
    let canvas = null;
    if (maxPreviewDimension) {
      if (bitmapWidth > maxPreviewDimension || bitmapHeight > maxPreviewDimension) {
        const ratio = Math.min(maxPreviewDimension / bitmapWidth, maxPreviewDimension / bitmapHeight);
        width = Math.floor(bitmapWidth * ratio);
        height = Math.floor(bitmapHeight * ratio);
      }
      canvas = document.createElement("canvas");
      const scaledWidth = canvas.width = Math.ceil(width * outputScale.sx);
      const scaledHeight = canvas.height = Math.ceil(height * outputScale.sy);
      if (!this.#isSvg) {
        bitmap = this.#scaleBitmap(scaledWidth, scaledHeight);
      }
      const ctx = canvas.getContext("2d");
      ctx.filter = this._uiManager.hcmFilter;
      let white = "white",
        black = "#cfcfd8";
      if (this._uiManager.hcmFilter !== "none") {
        black = "black";
      } else if (ColorScheme.isDarkMode) {
        white = "#8f8f9d";
        black = "#42414d";
      }
      const boxDim = 15;
      const boxDimWidth = boxDim * outputScale.sx;
      const boxDimHeight = boxDim * outputScale.sy;
      const pattern = new OffscreenCanvas(boxDimWidth * 2, boxDimHeight * 2);
      const patternCtx = pattern.getContext("2d");
      patternCtx.fillStyle = white;
      patternCtx.fillRect(0, 0, boxDimWidth * 2, boxDimHeight * 2);
      patternCtx.fillStyle = black;
      patternCtx.fillRect(0, 0, boxDimWidth, boxDimHeight);
      patternCtx.fillRect(boxDimWidth, boxDimHeight, boxDimWidth, boxDimHeight);
      ctx.fillStyle = ctx.createPattern(pattern, "repeat");
      ctx.fillRect(0, 0, scaledWidth, scaledHeight);
      ctx.drawImage(bitmap, 0, 0, bitmap.width, bitmap.height, 0, 0, scaledWidth, scaledHeight);
    }
    let imageData = null;
    if (createImageData) {
      let dataWidth, dataHeight;
      if (outputScale.symmetric && bitmap.width < maxDataDimension && bitmap.height < maxDataDimension) {
        dataWidth = bitmap.width;
        dataHeight = bitmap.height;
      } else {
        bitmap = this.#bitmap;
        if (bitmapWidth > maxDataDimension || bitmapHeight > maxDataDimension) {
          const ratio = Math.min(maxDataDimension / bitmapWidth, maxDataDimension / bitmapHeight);
          dataWidth = Math.floor(bitmapWidth * ratio);
          dataHeight = Math.floor(bitmapHeight * ratio);
          if (!this.#isSvg) {
            bitmap = this.#scaleBitmap(dataWidth, dataHeight);
          }
        }
      }
      const offscreen = new OffscreenCanvas(dataWidth, dataHeight);
      const offscreenCtx = offscreen.getContext("2d", {
        willReadFrequently: true
      });
      offscreenCtx.drawImage(bitmap, 0, 0, bitmap.width, bitmap.height, 0, 0, dataWidth, dataHeight);
      imageData = {
        width: dataWidth,
        height: dataHeight,
        data: offscreenCtx.getImageData(0, 0, dataWidth, dataHeight).data
      };
    }
    return {
      canvas,
      width,
      height,
      imageData
    };
  }
  #scaleBitmap(width, height) {
    const {
      width: bitmapWidth,
      height: bitmapHeight
    } = this.#bitmap;
    let newWidth = bitmapWidth;
    let newHeight = bitmapHeight;
    let bitmap = this.#bitmap;
    while (newWidth > 2 * width || newHeight > 2 * height) {
      const prevWidth = newWidth;
      const prevHeight = newHeight;
      if (newWidth > 2 * width) {
        newWidth = Math.ceil(newWidth / 2);
      }
      if (newHeight > 2 * height) {
        newHeight = Math.ceil(newHeight / 2);
      }
      const offscreen = new OffscreenCanvas(newWidth, newHeight);
      const ctx = offscreen.getContext("2d");
      ctx.drawImage(bitmap, 0, 0, prevWidth, prevHeight, 0, 0, newWidth, newHeight);
      bitmap = offscreen.transferToImageBitmap();
    }
    return bitmap;
  }
  #drawBitmap() {
    const [parentWidth, parentHeight] = this.parentDimensions;
    const {
      width,
      height
    } = this;
    const outputScale = new OutputScale();
    const scaledWidth = Math.ceil(width * parentWidth * outputScale.sx);
    const scaledHeight = Math.ceil(height * parentHeight * outputScale.sy);
    const canvas = this.#canvas;
    if (!canvas || canvas.width === scaledWidth && canvas.height === scaledHeight) {
      return;
    }
    canvas.width = scaledWidth;
    canvas.height = scaledHeight;
    const bitmap = this.#isSvg ? this.#bitmap : this.#scaleBitmap(scaledWidth, scaledHeight);
    const ctx = canvas.getContext("2d");
    ctx.filter = this._uiManager.hcmFilter;
    ctx.drawImage(bitmap, 0, 0, bitmap.width, bitmap.height, 0, 0, scaledWidth, scaledHeight);
  }
  #serializeBitmap(toUrl) {
    if (toUrl) {
      if (this.#isSvg) {
        const url = this._uiManager.imageManager.getSvgUrl(this.#bitmapId);
        if (url) {
          return url;
        }
      }
      const canvas = document.createElement("canvas");
      ({
        width: canvas.width,
        height: canvas.height
      } = this.#bitmap);
      const ctx = canvas.getContext("2d");
      ctx.drawImage(this.#bitmap, 0, 0);
      return canvas.toDataURL();
    }
    if (this.#isSvg) {
      const [pageWidth, pageHeight] = this.pageDimensions;
      const width = Math.round(this.width * pageWidth * PixelsPerInch.PDF_TO_CSS_UNITS);
      const height = Math.round(this.height * pageHeight * PixelsPerInch.PDF_TO_CSS_UNITS);
      const offscreen = new OffscreenCanvas(width, height);
      const ctx = offscreen.getContext("2d");
      ctx.drawImage(this.#bitmap, 0, 0, this.#bitmap.width, this.#bitmap.height, 0, 0, width, height);
      return offscreen.transferToImageBitmap();
    }
    return structuredClone(this.#bitmap);
  }
  static async deserialize(data, parent, uiManager) {
    let initialData = null;
    let missingCanvas = false;
    if (data instanceof StampAnnotationElement) {
      const {
        data: {
          rect,
          rotation,
          id,
          structParent,
          popupRef,
          richText,
          contentsObj,
          creationDate,
          modificationDate
        },
        container,
        parent: {
          page: {
            pageNumber
          }
        },
        canvas
      } = data;
      let bitmapId, bitmap;
      if (canvas) {
        delete data.canvas;
        ({
          id: bitmapId,
          bitmap
        } = uiManager.imageManager.getFromCanvas(container.id, canvas));
        canvas.remove();
      } else {
        missingCanvas = true;
        data._hasNoCanvas = true;
      }
      const altText = (await parent._structTree.getAriaAttributes(`${AnnotationPrefix}${id}`))?.get("aria-label") || "";
      initialData = data = {
        annotationType: AnnotationEditorType.STAMP,
        bitmapId,
        bitmap,
        pageIndex: pageNumber - 1,
        rect: rect.slice(0),
        rotation,
        annotationElementId: id,
        id,
        deleted: false,
        accessibilityData: {
          decorative: false,
          altText
        },
        isSvg: false,
        structParent,
        popupRef,
        richText,
        comment: contentsObj?.str || null,
        creationDate,
        modificationDate
      };
    }
    const editor = await super.deserialize(data, parent, uiManager);
    const {
      rect,
      bitmap,
      bitmapUrl,
      bitmapId,
      isSvg,
      accessibilityData
    } = data;
    if (missingCanvas) {
      uiManager.addMissingCanvas(data.id, editor);
      editor.#missingCanvas = true;
    } else if (bitmapId && uiManager.imageManager.isValidId(bitmapId)) {
      editor.#bitmapId = bitmapId;
      if (bitmap) {
        editor.#bitmap = bitmap;
      }
    } else {
      editor.#bitmapUrl = bitmapUrl;
    }
    editor.#isSvg = isSvg;
    const [parentWidth, parentHeight] = editor.pageDimensions;
    editor.width = (rect[2] - rect[0]) / parentWidth;
    editor.height = (rect[3] - rect[1]) / parentHeight;
    if (accessibilityData) {
      editor.altTextData = accessibilityData;
    }
    editor._initialData = initialData;
    if (data.comment) {
      editor.setCommentData(data);
    }
    editor.#hasBeenAddedInUndoStack = !!initialData;
    return editor;
  }
  serialize(isForCopying = false, context = null) {
    if (this.isEmpty()) {
      return null;
    }
    if (this.deleted) {
      return this.serializeDeleted();
    }
    const serialized = Object.assign(super.serialize(isForCopying), {
      bitmapId: this.#bitmapId,
      isSvg: this.#isSvg
    });
    this.addComment(serialized);
    if (isForCopying) {
      serialized.bitmapUrl = this.#serializeBitmap(true);
      serialized.accessibilityData = this.serializeAltText(true);
      serialized.isCopy = true;
      return serialized;
    }
    const {
      decorative,
      altText
    } = this.serializeAltText(false);
    if (!decorative && altText) {
      serialized.accessibilityData = {
        type: "Figure",
        alt: altText
      };
    }
    if (this.annotationElementId) {
      const changes = this.#hasElementChanged(serialized);
      if (changes.isSame) {
        return null;
      }
      if (changes.isSameAltText) {
        delete serialized.accessibilityData;
      } else {
        const structParent = this._initialData.structParent ?? -1;
        if (serialized.accessibilityData) {
          serialized.accessibilityData.structParent = structParent;
        } else if (structParent >= 0) {
          serialized.accessibilityData = {
            type: "Figure",
            alt: "",
            structParent
          };
        }
      }
      serialized.id = this.annotationElementId;
      delete serialized.bitmapId;
      return serialized;
    }
    if (context === null) {
      return serialized;
    }
    context.stamps ||= new Map();
    const area = this.#isSvg ? (serialized.rect[2] - serialized.rect[0]) * (serialized.rect[3] - serialized.rect[1]) : null;
    if (!context.stamps.has(this.#bitmapId)) {
      context.stamps.set(this.#bitmapId, {
        area,
        serialized
      });
      serialized.bitmap = this.#serializeBitmap(false);
    } else if (this.#isSvg) {
      const prevData = context.stamps.get(this.#bitmapId);
      if (area > prevData.area) {
        prevData.area = area;
        prevData.serialized.bitmap.close();
        prevData.serialized.bitmap = this.#serializeBitmap(false);
      }
    }
    return serialized;
  }
  #hasElementChanged(serialized) {
    const {
      pageIndex,
      accessibilityData: {
        altText
      }
    } = this._initialData;
    const isSamePageIndex = serialized.pageIndex === pageIndex;
    const isSameAltText = (serialized.accessibilityData?.alt || "") === altText;
    return {
      isSame: !this.hasEditedComment && !this._hasBeenMoved && !this._hasBeenResized && isSamePageIndex && isSameAltText,
      isSameAltText
    };
  }
  renderAnnotationElement(annotation) {
    if (this.deleted) {
      annotation.hide();
      return null;
    }
    annotation.updateEdited({
      rect: this.getPDFRect(),
      popup: this.comment
    });
    return null;
  }
}

;// ./src/display/editor/annotation_editor_layer.js








class AnnotationEditorLayer {
  #accessibilityManager;
  #allowClick = false;
  #annotationLayer = null;
  #clickAC = null;
  #editorFocusTimeoutId = null;
  #editors = new Map();
  #hadPointerDown = false;
  #isDisabling = false;
  #isEnabling = false;
  #drawingAC = null;
  #focusedElement = null;
  #textLayer = null;
  #textSelectionAC = null;
  #textLayerDblClickAC = null;
  #lastPointerDownTimestamp = -1;
  #uiManager;
  static _initialized = false;
  static #editorTypes = new Map([FreeTextEditor, InkEditor, StampEditor, HighlightEditor, SignatureEditor].map(type => [type._editorType, type]));
  constructor({
    uiManager,
    pageIndex,
    div,
    structTreeLayer,
    accessibilityManager,
    annotationLayer,
    drawLayer,
    textLayer,
    viewport,
    l10n
  }) {
    const editorTypes = [...AnnotationEditorLayer.#editorTypes.values()];
    if (!AnnotationEditorLayer._initialized) {
      AnnotationEditorLayer._initialized = true;
      for (const editorType of editorTypes) {
        editorType.initialize(l10n, uiManager);
      }
    }
    uiManager.registerEditorTypes(editorTypes);
    this.#uiManager = uiManager;
    this.pageIndex = pageIndex;
    this.div = div;
    this.#accessibilityManager = accessibilityManager;
    this.#annotationLayer = annotationLayer;
    this.viewport = viewport;
    this.#textLayer = textLayer;
    this.drawLayer = drawLayer;
    this._structTree = structTreeLayer;
    this.#uiManager.addLayer(this);
  }
  get isEmpty() {
    return this.#editors.size === 0;
  }
  get isInvisible() {
    return this.isEmpty && this.#uiManager.getMode() === AnnotationEditorType.NONE;
  }
  updateToolbar(options) {
    this.#uiManager.updateToolbar(options);
  }
  updateMode(mode = this.#uiManager.getMode()) {
    this.#cleanup();
    switch (mode) {
      case AnnotationEditorType.NONE:
        this.div.classList.toggle("nonEditing", true);
        this.disableTextSelection();
        this.togglePointerEvents(false);
        this.toggleAnnotationLayerPointerEvents(true);
        this.disableClick();
        return;
      case AnnotationEditorType.INK:
        this.disableTextSelection();
        this.togglePointerEvents(true);
        this.enableClick();
        break;
      case AnnotationEditorType.HIGHLIGHT:
        this.enableTextSelection();
        this.togglePointerEvents(false);
        this.disableClick();
        break;
      default:
        this.disableTextSelection();
        this.togglePointerEvents(true);
        this.enableClick();
    }
    this.toggleAnnotationLayerPointerEvents(false);
    const {
      classList
    } = this.div;
    classList.toggle("nonEditing", false);
    if (mode === AnnotationEditorType.POPUP) {
      classList.toggle("commentEditing", true);
    } else {
      classList.toggle("commentEditing", false);
      for (const editorType of AnnotationEditorLayer.#editorTypes.values()) {
        classList.toggle(`${editorType._type}Editing`, mode === editorType._editorType);
      }
    }
    this.div.hidden = false;
  }
  hasTextLayer(textLayer) {
    return textLayer === this.#textLayer?.div;
  }
  setEditingState(isEditing) {
    this.#uiManager.setEditingState(isEditing);
  }
  addCommands(params) {
    this.#uiManager.addCommands(params);
  }
  cleanUndoStack(type) {
    this.#uiManager.cleanUndoStack(type);
  }
  toggleDrawing(enabled = false) {
    this.div.classList.toggle("drawing", !enabled);
  }
  togglePointerEvents(enabled = false) {
    this.div.classList.toggle("disabled", !enabled);
  }
  toggleAnnotationLayerPointerEvents(enabled = false) {
    this.#annotationLayer?.togglePointerEvents(enabled);
  }
  get #allEditorsIterator() {
    return this.#editors.size !== 0 ? this.#editors.values() : this.#uiManager.getEditors(this.pageIndex);
  }
  async enable() {
    this.#isEnabling = true;
    this.div.tabIndex = 0;
    this.togglePointerEvents(true);
    this.div.classList.toggle("nonEditing", false);
    this.#textLayerDblClickAC?.abort();
    this.#textLayerDblClickAC = null;
    const annotationElementIds = new Set();
    for (const editor of this.#allEditorsIterator) {
      editor.enableEditing();
      editor.show(true);
      if (editor.annotationElementId) {
        this.#uiManager.removeChangedExistingAnnotation(editor);
        annotationElementIds.add(editor.annotationElementId);
      }
    }
    const annotationLayer = this.#annotationLayer;
    if (annotationLayer) {
      for (const editable of annotationLayer.getEditableAnnotations()) {
        editable.hide();
        if (this.#uiManager.isDeletedAnnotationElement(editable.data.id) || annotationElementIds.has(editable.data.id)) {
          continue;
        }
        const editor = await this.deserialize(editable);
        if (!editor) {
          continue;
        }
        this.addOrRebuild(editor);
        editor.enableEditing();
      }
    }
    this.#isEnabling = false;
    this.#uiManager._eventBus.dispatch("editorsrendered", {
      source: this,
      pageNumber: this.pageIndex + 1
    });
  }
  disable() {
    this.#isDisabling = true;
    this.div.tabIndex = -1;
    this.togglePointerEvents(false);
    this.div.classList.toggle("nonEditing", true);
    if (this.#textLayer && !this.#textLayerDblClickAC) {
      this.#textLayerDblClickAC = new AbortController();
      const signal = this.#uiManager.combinedSignal(this.#textLayerDblClickAC);
      this.#textLayer.div.addEventListener("pointerdown", e => {
        const DBL_CLICK_THRESHOLD = 500;
        const {
          clientX,
          clientY,
          timeStamp
        } = e;
        const lastPointerDownTimestamp = this.#lastPointerDownTimestamp;
        if (timeStamp - lastPointerDownTimestamp > DBL_CLICK_THRESHOLD) {
          this.#lastPointerDownTimestamp = timeStamp;
          return;
        }
        this.#lastPointerDownTimestamp = -1;
        const {
          classList
        } = this.div;
        classList.toggle("getElements", true);
        const elements = document.elementsFromPoint(clientX, clientY);
        classList.toggle("getElements", false);
        if (!this.div.contains(elements[0])) {
          return;
        }
        let id;
        const regex = new RegExp(`^${AnnotationEditorPrefix}[0-9]+$`);
        for (const element of elements) {
          if (regex.test(element.id)) {
            id = element.id;
            break;
          }
        }
        if (!id) {
          return;
        }
        const editor = this.#editors.get(id);
        if (editor?.annotationElementId === null) {
          stopEvent(e);
          editor.dblclick(e);
        }
      }, {
        signal,
        capture: true
      });
    }
    const annotationLayer = this.#annotationLayer;
    const needFakeAnnotation = [];
    if (annotationLayer) {
      const changedAnnotations = new Map();
      const resetAnnotations = new Map();
      for (const editor of this.#allEditorsIterator) {
        editor.disableEditing();
        if (!editor.annotationElementId) {
          needFakeAnnotation.push(editor);
          continue;
        }
        if (editor.serialize() !== null) {
          changedAnnotations.set(editor.annotationElementId, editor);
          continue;
        } else {
          resetAnnotations.set(editor.annotationElementId, editor);
        }
        this.getEditableAnnotation(editor.annotationElementId)?.show();
        editor.remove();
      }
      for (const editable of annotationLayer.getEditableAnnotations()) {
        const {
          id
        } = editable.data;
        if (this.#uiManager.isDeletedAnnotationElement(id)) {
          editable.updateEdited({
            deleted: true
          });
          continue;
        }
        let editor = resetAnnotations.get(id);
        if (editor) {
          editor.resetAnnotationElement(editable);
          editor.show(false);
          editable.show();
          continue;
        }
        editor = changedAnnotations.get(id);
        if (editor) {
          this.#uiManager.addChangedExistingAnnotation(editor);
          if (editor.renderAnnotationElement(editable)) {
            editor.show(false);
          }
        }
        editable.show();
      }
    }
    this.#cleanup();
    if (this.isEmpty) {
      this.div.hidden = true;
    }
    const {
      classList
    } = this.div;
    for (const editorType of AnnotationEditorLayer.#editorTypes.values()) {
      classList.remove(`${editorType._type}Editing`);
    }
    this.disableTextSelection();
    this.toggleAnnotationLayerPointerEvents(true);
    annotationLayer?.updateFakeAnnotations(needFakeAnnotation);
    this.#isDisabling = false;
  }
  getEditableAnnotation(id) {
    return this.#annotationLayer?.getEditableAnnotation(id) || null;
  }
  setActiveEditor(editor) {
    const currentActive = this.#uiManager.getActive();
    if (currentActive === editor) {
      return;
    }
    this.#uiManager.setActiveEditor(editor);
  }
  enableTextSelection() {
    this.div.tabIndex = -1;
    if (this.#textLayer?.div && !this.#textSelectionAC) {
      this.#textSelectionAC = new AbortController();
      const signal = this.#uiManager.combinedSignal(this.#textSelectionAC);
      this.#textLayer.div.addEventListener("pointerdown", this.#textLayerPointerDown.bind(this), {
        signal
      });
      this.#textLayer.div.classList.add("highlighting");
    }
  }
  disableTextSelection() {
    this.div.tabIndex = 0;
    if (this.#textLayer?.div && this.#textSelectionAC) {
      this.#textSelectionAC.abort();
      this.#textSelectionAC = null;
      this.#textLayer.div.classList.remove("highlighting");
    }
  }
  #textLayerPointerDown(event) {
    this.#uiManager.unselectAll();
    const {
      target
    } = event;
    if (target === this.#textLayer.div || (target.getAttribute("role") === "img" || target.classList.contains("endOfContent") || target.classList.contains("textLayerImages") || target.classList.contains("textLayerImagePlaceholder")) && this.#textLayer.div.contains(target)) {
      const {
        isMac
      } = FeatureTest.platform;
      if (event.button !== 0 || event.ctrlKey && isMac) {
        return;
      }
      this.#uiManager.showAllEditors("highlight", true, true);
      HighlightEditor.startDrawing(this, this.#uiManager, this.#uiManager.direction === "ltr", event);
      event.preventDefault();
    }
  }
  enableClick() {
    if (this.#clickAC) {
      return;
    }
    this.#clickAC = new AbortController();
    const signal = this.#uiManager.combinedSignal(this.#clickAC);
    this.div.addEventListener("pointerdown", this.pointerdown.bind(this), {
      signal
    });
    const pointerup = this.pointerup.bind(this);
    this.div.addEventListener("pointerup", pointerup, {
      signal
    });
    this.div.addEventListener("pointercancel", pointerup, {
      signal
    });
  }
  disableClick() {
    this.#clickAC?.abort();
    this.#clickAC = null;
  }
  attach(editor) {
    this.#editors.set(editor.id, editor);
    const {
      annotationElementId
    } = editor;
    if (annotationElementId && this.#uiManager.isDeletedAnnotationElement(annotationElementId)) {
      this.#uiManager.removeDeletedAnnotationElement(editor);
    }
  }
  detach(editor) {
    this.#editors.delete(editor.id);
    this.#accessibilityManager?.removePointerInTextLayer(editor.contentDiv);
    if (!this.#isDisabling && editor.annotationElementId) {
      this.#uiManager.addDeletedAnnotationElement(editor);
    }
  }
  remove(editor) {
    this.detach(editor);
    this.#uiManager.removeEditor(editor);
    editor.div.remove();
    editor.isAttachedToDOM = false;
  }
  changeParent(editor) {
    if (editor.parent === this) {
      return;
    }
    if (editor.parent && editor.annotationElementId) {
      this.#uiManager.addDeletedAnnotationElement(editor);
      AnnotationEditor.deleteAnnotationElement(editor);
      editor.annotationElementId = null;
    }
    this.attach(editor);
    editor.parent?.detach(editor);
    editor.setParent(this);
    if (editor.div && editor.isAttachedToDOM) {
      editor.div.remove();
      this.div.append(editor.div);
    }
  }
  add(editor) {
    if (editor.parent === this && editor.isAttachedToDOM) {
      return;
    }
    this.changeParent(editor);
    this.#uiManager.addEditor(editor);
    this.attach(editor);
    if (!editor.isAttachedToDOM) {
      const div = editor.render();
      this.div.append(div);
      editor.isAttachedToDOM = true;
    }
    editor.fixAndSetPosition();
    editor.onceAdded(!this.#isEnabling);
    this.#uiManager.addToAnnotationStorage(editor);
    editor._reportTelemetry(editor.telemetryInitialData);
  }
  moveEditorInDOM(editor) {
    if (!editor.isAttachedToDOM) {
      return;
    }
    const {
      activeElement
    } = document;
    if (editor.div.contains(activeElement) && !this.#editorFocusTimeoutId) {
      editor._focusEventsAllowed = false;
      this.#editorFocusTimeoutId = setTimeout(() => {
        this.#editorFocusTimeoutId = null;
        if (!editor.div.contains(document.activeElement)) {
          editor.div.addEventListener("focusin", () => {
            editor._focusEventsAllowed = true;
          }, {
            once: true,
            signal: this.#uiManager._signal
          });
          activeElement.focus();
        } else {
          editor._focusEventsAllowed = true;
        }
      }, 0);
    }
    editor._structTreeParentId = this.#accessibilityManager?.moveElementInDOM(this.div, editor.div, editor.contentDiv, true);
  }
  addOrRebuild(editor) {
    if (editor.needsToBeRebuilt()) {
      editor.parent ||= this;
      editor.rebuild();
      editor.show();
    } else {
      this.add(editor);
    }
  }
  addUndoableEditor(editor) {
    const cmd = () => editor._uiManager.rebuild(editor);
    const undo = () => {
      editor.remove();
    };
    this.addCommands({
      cmd,
      undo,
      mustExec: false
    });
  }
  getEditorByUID(uid) {
    for (const editor of this.#editors.values()) {
      if (editor.uid === uid) {
        return editor;
      }
    }
    return null;
  }
  get #currentEditorType() {
    return AnnotationEditorLayer.#editorTypes.get(this.#uiManager.getMode());
  }
  combinedSignal(ac) {
    return this.#uiManager.combinedSignal(ac);
  }
  #createNewEditor(params) {
    const editorType = this.#currentEditorType;
    return editorType ? new editorType.prototype.constructor(params) : null;
  }
  canCreateNewEmptyEditor() {
    return this.#currentEditorType?.canCreateNewEmptyEditor();
  }
  async pasteEditor(options, params) {
    this.updateToolbar(options);
    await this.#uiManager.updateMode(options.mode);
    const {
      offsetX,
      offsetY
    } = this.#getCenterPoint();
    const id = this.#uiManager.getId();
    const editor = this.#createNewEditor({
      parent: this,
      id,
      x: offsetX,
      y: offsetY,
      uiManager: this.#uiManager,
      isCentered: true,
      ...params
    });
    if (editor) {
      this.add(editor);
    }
  }
  async deserialize(data) {
    return (await AnnotationEditorLayer.#editorTypes.get(data.annotationType ?? data.annotationEditorType)?.deserialize(data, this, this.#uiManager)) || null;
  }
  createAndAddNewEditor(event, isCentered, data = {}) {
    const id = this.#uiManager.getId();
    const editor = this.#createNewEditor({
      parent: this,
      id,
      x: event.offsetX,
      y: event.offsetY,
      uiManager: this.#uiManager,
      isCentered,
      ...data
    });
    if (editor) {
      this.add(editor);
    }
    return editor;
  }
  get boundingClientRect() {
    return this.div.getBoundingClientRect();
  }
  #getCenterPoint() {
    const {
      x,
      y,
      width,
      height
    } = this.boundingClientRect;
    const tlX = Math.max(0, x);
    const tlY = Math.max(0, y);
    const brX = Math.min(window.innerWidth, x + width);
    const brY = Math.min(window.innerHeight, y + height);
    const centerX = (tlX + brX) / 2 - x;
    const centerY = (tlY + brY) / 2 - y;
    const [offsetX, offsetY] = this.viewport.rotation % 180 === 0 ? [centerX, centerY] : [centerY, centerX];
    return {
      offsetX,
      offsetY
    };
  }
  addNewEditor(data = {}) {
    this.createAndAddNewEditor(this.#getCenterPoint(), true, data);
  }
  setSelected(editor) {
    this.#uiManager.setSelected(editor);
  }
  toggleSelected(editor) {
    this.#uiManager.toggleSelected(editor);
  }
  unselect(editor) {
    this.#uiManager.unselect(editor);
  }
  pointerup(event) {
    const {
      isMac
    } = FeatureTest.platform;
    if (event.button !== 0 || event.ctrlKey && isMac) {
      return;
    }
    if (event.target !== this.div) {
      return;
    }
    if (!this.#hadPointerDown) {
      return;
    }
    this.#hadPointerDown = false;
    if (this.#currentEditorType?.isDrawer && this.#currentEditorType.supportMultipleDrawings) {
      return;
    }
    if (!this.#allowClick) {
      this.#allowClick = true;
      return;
    }
    const currentMode = this.#uiManager.getMode();
    if (currentMode === AnnotationEditorType.STAMP || currentMode === AnnotationEditorType.POPUP || currentMode === AnnotationEditorType.SIGNATURE) {
      this.#uiManager.unselectAll();
      return;
    }
    this.createAndAddNewEditor(event, false);
  }
  pointerdown(event) {
    if (this.#uiManager.getMode() === AnnotationEditorType.HIGHLIGHT) {
      this.enableTextSelection();
    }
    if (this.#hadPointerDown) {
      this.#hadPointerDown = false;
      return;
    }
    const {
      isMac
    } = FeatureTest.platform;
    if (event.button !== 0 || event.ctrlKey && isMac) {
      return;
    }
    if (event.target !== this.div) {
      return;
    }
    this.#hadPointerDown = true;
    if (this.#currentEditorType?.isDrawer) {
      this.startDrawingSession(event);
      return;
    }
    const editor = this.#uiManager.getActive();
    this.#allowClick = !editor || editor.isEmpty();
  }
  startDrawingSession(event) {
    this.div.focus({
      preventScroll: true
    });
    if (this.#drawingAC) {
      this.#currentEditorType.startDrawing(this, this.#uiManager, false, event);
      return;
    }
    this.#uiManager.setCurrentDrawingSession(this);
    this.#drawingAC = new AbortController();
    const signal = this.#uiManager.combinedSignal(this.#drawingAC);
    this.div.addEventListener("blur", ({
      relatedTarget
    }) => {
      if (relatedTarget && !this.div.contains(relatedTarget)) {
        this.#focusedElement = null;
        this.commitOrRemove();
      }
    }, {
      signal
    });
    this.#currentEditorType.startDrawing(this, this.#uiManager, false, event);
  }
  pause(on) {
    if (on) {
      const {
        activeElement
      } = document;
      if (this.div.contains(activeElement)) {
        this.#focusedElement = activeElement;
      }
      return;
    }
    if (this.#focusedElement) {
      setTimeout(() => {
        this.#focusedElement?.focus();
        this.#focusedElement = null;
      }, 0);
    }
  }
  endDrawingSession(isAborted = false) {
    if (!this.#drawingAC) {
      return null;
    }
    this.#uiManager.setCurrentDrawingSession(null);
    this.#drawingAC.abort();
    this.#drawingAC = null;
    this.#focusedElement = null;
    return this.#currentEditorType.endDrawing(isAborted);
  }
  findNewParent(editor, x, y) {
    const layer = this.#uiManager.findParent(x, y);
    if (layer === null || layer === this) {
      return false;
    }
    layer.changeParent(editor);
    return true;
  }
  commitOrRemove() {
    if (this.#drawingAC) {
      this.endDrawingSession();
      return true;
    }
    return false;
  }
  onScaleChanging() {
    if (!this.#drawingAC) {
      return;
    }
    this.#currentEditorType.onScaleChangingWhenDrawing(this);
  }
  destroy() {
    this.commitOrRemove();
    if (this.#uiManager.getActive()?.parent === this) {
      this.#uiManager.commitOrRemove();
      this.#uiManager.setActiveEditor(null);
    }
    if (this.#editorFocusTimeoutId) {
      clearTimeout(this.#editorFocusTimeoutId);
      this.#editorFocusTimeoutId = null;
    }
    for (const editor of this.#editors.values()) {
      this.#accessibilityManager?.removePointerInTextLayer(editor.contentDiv);
      editor.setParent(null);
      editor.isAttachedToDOM = false;
      editor.div.remove();
    }
    this.div = null;
    this.#editors.clear();
    this.#uiManager.removeLayer(this);
  }
  #cleanup() {
    for (const editor of this.#editors.values()) {
      if (editor.isEmpty()) {
        editor.remove();
      }
    }
  }
  async render({
    viewport
  }) {
    this.viewport = viewport;
    setLayerDimensions(this.div, viewport);
    for (const editor of this.#uiManager.getEditors(this.pageIndex)) {
      this.add(editor);
      editor.rebuild();
    }
    await this.#uiManager.findClonesForPage(this);
    this.div.hidden = this.isEmpty;
    this.updateMode();
  }
  update({
    viewport
  }) {
    this.#uiManager.commitOrRemove();
    this.#cleanup();
    const oldRotation = this.viewport.rotation;
    const rotation = viewport.rotation;
    this.viewport = viewport;
    setLayerDimensions(this.div, {
      rotation
    });
    if (oldRotation !== rotation) {
      for (const editor of this.#editors.values()) {
        editor.rotate(rotation);
      }
    }
  }
  get pageDimensions() {
    const {
      pageWidth,
      pageHeight
    } = this.viewport.rawDims;
    return [pageWidth, pageHeight];
  }
  get scale() {
    return this.#uiManager.viewParameters.realScale;
  }
}

;// ./src/display/draw_layer.js


function compareTextLayers(a, b) {
  if (a === b) {
    return 0;
  }
  return a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING ? -1 : 1;
}
function getTextLayer(node) {
  if (!node) {
    return null;
  }
  return node.nodeType === Node.ELEMENT_NODE ? node.closest(".textLayer") : node.parentElement?.closest(".textLayer") || null;
}
function isPointBefore(nodeA, offsetA, nodeB, offsetB) {
  if (nodeA === nodeB) {
    return offsetA <= offsetB;
  }
  const relation = nodeA.compareDocumentPosition(nodeB);
  if (relation & Node.DOCUMENT_POSITION_FOLLOWING) {
    return true;
  }
  if (relation & Node.DOCUMENT_POSITION_PRECEDING) {
    return false;
  }
  return null;
}
function normalizeEdgeBoundary(container, offset, textLayer) {
  if (container.nodeType !== Node.ELEMENT_NODE || !container.classList.contains("textLayer") || offset !== container.childNodes.length) {
    return {
      container,
      offset
    };
  }
  let lastNode = container.lastChild;
  if (lastNode?.nodeType === Node.ELEMENT_NODE && lastNode.classList.contains("endOfContent")) {
    lastNode = lastNode.previousSibling;
  }
  if (!lastNode || !textLayer.contains(lastNode)) {
    return null;
  }
  return lastNode.nodeType === Node.TEXT_NODE ? {
    container: lastNode,
    offset: lastNode.textContent.length
  } : {
    container: lastNode,
    offset: lastNode.childNodes.length
  };
}
class DrawLayer {
  #parent = null;
  #mapping = new Map();
  #textLayer = null;
  #filterFactory = null;
  #pageColors = null;
  #textLayerObserver = null;
  #toUpdate = new Map();
  static #id = 0;
  static #selectionId = 0;
  static #selectionChangeAC = null;
  static #selections = new Set();
  static #isSelecting = false;
  static #textLayerSet = new Set();
  static #textLayers = new WeakMap();
  constructor({
    filterFactory = null,
    pageColors = null,
    pageIndex,
    textLayer = null
  }) {
    this.pageIndex = pageIndex;
    this.#filterFactory = filterFactory;
    this.#pageColors = pageColors;
    if (textLayer) {
      const previousData = DrawLayer.#textLayers.get(textLayer);
      if (previousData?.selectionDiv) {
        previousData.selectionDiv.remove();
        DrawLayer.#selections.delete(previousData.selectionDiv);
      }
      DrawLayer.#textLayers.set(textLayer, {
        drawLayer: this
      });
      DrawLayer.#textLayerSet.add(textLayer);
      this.#textLayer = textLayer;
      this.#textLayerObserver = new MutationObserver(records => {
        if (!this.#parent || !this.#textLayer?.isConnected || !DrawLayer.#hasSelection()) {
          return;
        }
        for (const {
          addedNodes
        } of records) {
          for (const node of addedNodes) {
            if (node.nodeType === Node.ELEMENT_NODE && node.classList.contains("endOfContent")) {
              DrawLayer.#selectionChange();
              return;
            }
          }
        }
      });
      this.#textLayerObserver.observe(textLayer, {
        childList: true
      });
      if (DrawLayer.#selectionChangeAC === null) {
        DrawLayer.#selectionChangeAC = new AbortController();
        const {
          signal
        } = DrawLayer.#selectionChangeAC;
        document.addEventListener("selectionchange", DrawLayer.#selectionChange.bind(DrawLayer), {
          signal
        });
        document.addEventListener("pointerdown", () => {
          DrawLayer.#isSelecting = true;
        }, {
          signal
        });
        document.addEventListener("pointerup", () => {
          DrawLayer.#isSelecting = false;
        }, {
          signal
        });
        window.addEventListener("blur", () => {
          DrawLayer.#isSelecting = false;
        }, {
          signal
        });
      }
    }
  }
  setParent(parent) {
    if (!this.#parent) {
      this.#parent = parent;
      if (this.#textLayer?.isConnected && DrawLayer.#hasSelection()) {
        DrawLayer.#selectionChange();
      }
      return;
    }
    if (this.#parent !== parent) {
      if (this.#mapping.size > 0) {
        for (const root of this.#mapping.values()) {
          root.remove();
          parent.append(root);
        }
      }
      this.#parent = parent;
    }
  }
  static #cleanupTextLayerSelection(textLayer) {
    const textLayerData = this.#textLayers.get(textLayer);
    if (!textLayerData?.selectionDiv) {
      return;
    }
    textLayerData.selectionDiv.remove();
    this.#selections.delete(textLayerData.selectionDiv);
    textLayerData.selectionDiv = null;
    textLayerData.path = null;
  }
  static #hasSelection() {
    const selection = document.getSelection();
    return !!selection && !selection.isCollapsed;
  }
  static #getOrderedTextLayers() {
    return this.#textLayerSet.keys().filter(textLayer => textLayer.isConnected).toArray().sort(compareTextLayers);
  }
  static #selectionChange() {
    const selection = document.getSelection();
    if (!selection || selection.isCollapsed) {
      for (const root of this.#selections) {
        root.remove();
      }
      this.#selections.clear();
      return;
    }
    const rotators = new WeakMap();
    const orderedTextLayers = this.#getOrderedTextLayers();
    const ranges = [];
    for (let i = 0, ii = selection.rangeCount; i < ii; i++) {
      const range = selection.getRangeAt(i);
      if (range.collapsed) {
        continue;
      }
      let {
        startContainer,
        startOffset,
        endContainer,
        endOffset
      } = range;
      let startTextLayer = getTextLayer(startContainer);
      let endTextLayer = getTextLayer(endContainer);
      const startMissing = startTextLayer === null;
      const endMissing = endTextLayer === null;
      if (this.#isSelecting && startMissing !== endMissing) {
        return;
      }
      if (selection.rangeCount === 1) {
        const {
          anchorNode,
          anchorOffset,
          focusNode,
          focusOffset
        } = selection;
        const anchorLayer = getTextLayer(anchorNode);
        const focusLayer = getTextLayer(focusNode);
        const anchorBeforeFocus = isPointBefore(anchorNode, anchorOffset, focusNode, focusOffset);
        if (anchorLayer && focusLayer && anchorBeforeFocus !== null) {
          if (anchorBeforeFocus) {
            startContainer = anchorNode;
            startOffset = anchorOffset;
            startTextLayer = anchorLayer;
            endContainer = focusNode;
            endOffset = focusOffset;
            endTextLayer = focusLayer;
          } else {
            startContainer = focusNode;
            startOffset = focusOffset;
            startTextLayer = focusLayer;
            endContainer = anchorNode;
            endOffset = anchorOffset;
            endTextLayer = anchorLayer;
          }
        }
      }
      const activeTextLayers = orderedTextLayers.filter(textLayer => range.intersectsNode(textLayer));
      if (activeTextLayers.length === 0) {
        continue;
      }
      let boundarySubstituted = false;
      if (!startTextLayer) {
        startTextLayer = activeTextLayers[0];
        startContainer = startTextLayer;
        startOffset = 0;
        boundarySubstituted = true;
      }
      if (!endTextLayer) {
        endTextLayer = activeTextLayers.at(-1);
        endContainer = endTextLayer;
        endOffset = endTextLayer.childNodes.length;
        boundarySubstituted = true;
      }
      if (endContainer.nodeType === Node.ELEMENT_NODE) {
        if (endContainer.classList.contains("endOfContent")) {
          const previousNode = endContainer.previousSibling;
          if (!previousNode) {
            continue;
          }
          endContainer = previousNode;
          endOffset = previousNode.nodeType === Node.TEXT_NODE ? previousNode.textContent.length : previousNode.childNodes.length;
        } else if (endContainer.classList.contains("textLayer") && endContainer.childNodes.length === endOffset) {
          const normalizedEnd = normalizeEdgeBoundary(endContainer, endOffset, endTextLayer);
          if (!normalizedEnd) {
            continue;
          }
          endContainer = normalizedEnd.container;
          endOffset = normalizedEnd.offset;
        }
      }
      if (startContainer.nodeType === Node.ELEMENT_NODE) {
        const normalizedStart = normalizeEdgeBoundary(startContainer, startOffset, startTextLayer);
        if (!normalizedStart) {
          continue;
        }
        startContainer = normalizedStart.container;
        startOffset = normalizedStart.offset;
      }
      if (startTextLayer === endTextLayer && !boundarySubstituted && activeTextLayers.includes(startTextLayer)) {
        ranges.push([range, startTextLayer]);
        continue;
      }
      for (const textLayer of activeTextLayers) {
        const firstNode = textLayer.firstChild;
        if (!firstNode) {
          continue;
        }
        const subRange = document.createRange();
        if (textLayer === startTextLayer) {
          subRange.setStart(startContainer, startOffset);
        } else {
          subRange.setStartBefore(firstNode);
        }
        if (textLayer === endTextLayer) {
          subRange.setEnd(endContainer, endOffset);
        } else {
          const lastNode = textLayer.lastChild;
          if (!lastNode) {
            continue;
          }
          if (lastNode.nodeType === Node.ELEMENT_NODE && lastNode.classList.contains("endOfContent")) {
            const lastTextNode = lastNode.previousSibling;
            if (!lastTextNode) {
              continue;
            }
            subRange.setEndAfter(lastTextNode);
          } else {
            subRange.setEndAfter(lastNode);
          }
        }
        if (!subRange.collapsed) {
          ranges.push([subRange, textLayer]);
        }
      }
    }
    const selectedTextLayers = new Set(ranges.map(range => range[1]));
    for (const textLayer of this.#textLayerSet) {
      if (!selectedTextLayers.has(textLayer)) {
        this.#cleanupTextLayerSelection(textLayer);
      }
    }
    for (const [range, textLayer] of ranges) {
      const textLayerData = DrawLayer.#textLayers.get(textLayer);
      if (!textLayerData) {
        continue;
      }
      let rotator = rotators.get(textLayer);
      if (!rotator) {
        const clientRect = textLayer.getBoundingClientRect();
        rotator = (x, y, w, h) => ({
          x: (x - clientRect.x) / clientRect.width,
          y: (y - clientRect.y) / clientRect.height,
          width: w / clientRect.width,
          height: h / clientRect.height
        });
        rotators.set(textLayer, rotator);
      }
      const boxes = [];
      for (let {
        x,
        y,
        width,
        height
      } of range.getClientRects()) {
        if (width === 0 || height === 0) {
          continue;
        }
        ({
          x,
          y,
          width,
          height
        } = rotator(x, y, width, height));
        if (width === 1 && height === 1) {
          continue;
        }
        boxes.push(`M${x} ${y} h${width} v${height} h-${width} Z`);
      }
      if (boxes.length === 0) {
        continue;
      }
      const drawLayer = textLayerData.drawLayer;
      let div = textLayerData.selectionDiv;
      let path = textLayerData.path;
      if (!div) {
        const clipPathId = `clip_selection_${DrawLayer.#selectionId++}`;
        div = document.createElement("div");
        div.className = "selection";
        div.style.clipPath = `url(#${clipPathId})`;
        const selectionStyle = drawLayer.#filterFactory?.createSelectionStyle(drawLayer.#pageColors);
        if (selectionStyle) {
          for (const [name, value] of Object.entries(selectionStyle)) {
            div.style.setProperty(name, value);
          }
        }
        const svg = DrawLayer._svgFactory.create(1, 1, true);
        svg.setAttribute("aria-hidden", "true");
        svg.setAttribute("width", "100%");
        svg.setAttribute("height", "100%");
        const clipPath = DrawLayer._svgFactory.createElement("clipPath");
        clipPath.setAttribute("id", clipPathId);
        clipPath.setAttribute("clipPathUnits", "objectBoundingBox");
        path = DrawLayer._svgFactory.createElement("path");
        clipPath.append(path);
        svg.append(clipPath);
        div.append(svg);
        textLayerData.path = path;
        textLayerData.selectionDiv = div;
      }
      if (drawLayer.#parent && div.parentNode !== drawLayer.#parent) {
        drawLayer.#parent.append(div);
        this.#selections.add(div);
      }
      path.setAttribute("d", boxes.join(" "));
    }
  }
  static get _svgFactory() {
    return shadow(this, "_svgFactory", new DOMSVGFactory());
  }
  static #setBox(element, [x, y, width, height]) {
    const {
      style
    } = element;
    style.top = `${100 * y}%`;
    style.left = `${100 * x}%`;
    style.width = `${100 * width}%`;
    style.height = `${100 * height}%`;
  }
  #createSVG() {
    const svg = DrawLayer._svgFactory.create(1, 1, true);
    this.#parent.append(svg);
    svg.setAttribute("aria-hidden", "true");
    return svg;
  }
  #createClipPath(defs, pathId) {
    const clipPath = DrawLayer._svgFactory.createElement("clipPath");
    defs.append(clipPath);
    const clipPathId = `clip_${pathId}`;
    clipPath.setAttribute("id", clipPathId);
    clipPath.setAttribute("clipPathUnits", "objectBoundingBox");
    const clipPathUse = DrawLayer._svgFactory.createElement("use");
    clipPath.append(clipPathUse);
    clipPathUse.setAttribute("href", `#${pathId}`);
    clipPathUse.classList.add("clip");
    return clipPathId;
  }
  #updateProperties(element, properties) {
    for (const [key, value] of Object.entries(properties)) {
      if (value === null) {
        element.removeAttribute(key);
      } else {
        element.setAttribute(key, value);
      }
    }
  }
  draw(properties, isPathUpdatable = false, hasClip = false) {
    const id = DrawLayer.#id++;
    const root = this.#createSVG();
    const defs = DrawLayer._svgFactory.createElement("defs");
    root.append(defs);
    const path = DrawLayer._svgFactory.createElement("path");
    defs.append(path);
    const pathId = `path_${id}`;
    path.setAttribute("id", pathId);
    path.setAttribute("vector-effect", "non-scaling-stroke");
    if (isPathUpdatable) {
      this.#toUpdate.set(id, path);
    }
    const clipPathId = hasClip ? this.#createClipPath(defs, pathId) : null;
    const use = DrawLayer._svgFactory.createElement("use");
    root.append(use);
    use.setAttribute("href", `#${pathId}`);
    this.updateProperties(root, properties);
    this.#mapping.set(id, root);
    return {
      id,
      clipPathId: `url(#${clipPathId})`
    };
  }
  drawOutline(properties, mustRemoveSelfIntersections) {
    const id = DrawLayer.#id++;
    const root = this.#createSVG();
    const defs = DrawLayer._svgFactory.createElement("defs");
    root.append(defs);
    const path = DrawLayer._svgFactory.createElement("path");
    defs.append(path);
    const pathId = `path_${id}`;
    path.setAttribute("id", pathId);
    path.setAttribute("vector-effect", "non-scaling-stroke");
    let maskId;
    if (mustRemoveSelfIntersections) {
      const mask = DrawLayer._svgFactory.createElement("mask");
      defs.append(mask);
      maskId = `mask_${id}`;
      mask.setAttribute("id", maskId);
      mask.setAttribute("maskUnits", "objectBoundingBox");
      const rect = DrawLayer._svgFactory.createElement("rect");
      mask.append(rect);
      rect.setAttribute("width", "1");
      rect.setAttribute("height", "1");
      rect.setAttribute("fill", "white");
      const use = DrawLayer._svgFactory.createElement("use");
      mask.append(use);
      use.setAttribute("href", `#${pathId}`);
      use.setAttribute("stroke", "none");
      use.setAttribute("fill", "black");
      use.setAttribute("fill-rule", "nonzero");
      use.classList.add("mask");
    }
    const use1 = DrawLayer._svgFactory.createElement("use");
    root.append(use1);
    use1.setAttribute("href", `#${pathId}`);
    if (maskId) {
      use1.setAttribute("mask", `url(#${maskId})`);
    }
    const use2 = use1.cloneNode();
    root.append(use2);
    use1.classList.add("mainOutline");
    use2.classList.add("secondaryOutline");
    this.updateProperties(root, properties);
    this.#mapping.set(id, root);
    return id;
  }
  finalizeDraw(id, properties) {
    this.#toUpdate.delete(id);
    this.updateProperties(id, properties);
  }
  updateProperties(elementOrId, properties) {
    if (!properties) {
      return;
    }
    const {
      root,
      bbox,
      rootClass,
      path
    } = properties;
    const element = typeof elementOrId === "number" ? this.#mapping.get(elementOrId) : elementOrId;
    if (!element) {
      return;
    }
    if (root) {
      this.#updateProperties(element, root);
    }
    if (bbox) {
      DrawLayer.#setBox(element, bbox);
    }
    if (rootClass) {
      const {
        classList
      } = element;
      for (const [className, value] of Object.entries(rootClass)) {
        classList.toggle(className, value);
      }
    }
    if (path) {
      const defs = element.firstElementChild;
      const pathElement = defs.firstElementChild;
      this.#updateProperties(pathElement, path);
    }
  }
  updateParent(id, layer) {
    if (layer === this) {
      return;
    }
    const root = this.#mapping.get(id);
    if (!root) {
      return;
    }
    layer.#parent.append(root);
    this.#mapping.delete(id);
    layer.#mapping.set(id, root);
  }
  remove(id) {
    this.#toUpdate.delete(id);
    if (this.#parent === null) {
      return;
    }
    this.#mapping.get(id).remove();
    this.#mapping.delete(id);
  }
  destroy() {
    this.#parent = null;
    for (const root of this.#mapping.values()) {
      root.remove();
    }
    this.#mapping.clear();
    this.#toUpdate.clear();
    this.#textLayerObserver?.disconnect();
    this.#textLayerObserver = null;
    if (this.#textLayer) {
      const data = DrawLayer.#textLayers.get(this.#textLayer);
      if (data?.drawLayer === this) {
        DrawLayer.#cleanupTextLayerSelection(this.#textLayer);
        DrawLayer.#textLayers.delete(this.#textLayer);
        DrawLayer.#textLayerSet.delete(this.#textLayer);
        if (DrawLayer.#textLayerSet.size === 0) {
          DrawLayer.#selectionChangeAC?.abort();
          DrawLayer.#selectionChangeAC = null;
          DrawLayer.#isSelecting = false;
        }
      }
      this.#textLayer = null;
    }
  }
}

;// ./src/display/text_layer_images.js

function percentage(value) {
  return `${(value * 100).toFixed(2)}%`;
}
class TextLayerImages {
  #coordinates = [];
  #coordinatesByElement = new Map();
  #getPageCanvas = null;
  #minSize = 0;
  #pageWidth = 0;
  #pageHeight = 0;
  static #activeImage = null;
  constructor(minSize, coordinates, viewport, getPageCanvas) {
    this.#minSize = minSize;
    this.#coordinates = coordinates;
    this.#pageWidth = viewport.rawDims.pageWidth;
    this.#pageHeight = viewport.rawDims.pageHeight;
    this.#getPageCanvas = getPageCanvas;
  }
  render() {
    const container = document.createElement("div");
    container.className = "textLayerImages";
    for (let i = 0; i < this.#coordinates.length; i += 6) {
      const el = this.#createImagePlaceholder(this.#coordinates.subarray(i, i + 6));
      if (el) {
        container.append(el);
      }
    }
    container.addEventListener("contextmenu", event => {
      if (!(event.target instanceof HTMLCanvasElement)) {
        return;
      }
      const imgElement = event.target;
      const coords = this.#coordinatesByElement.get(imgElement);
      if (!coords) {
        return;
      }
      const activeImage = TextLayerImages.#activeImage?.deref();
      if (activeImage === imgElement) {
        return;
      }
      if (activeImage) {
        activeImage.width = 0;
        activeImage.height = 0;
      }
      TextLayerImages.#activeImage = new WeakRef(imgElement);
      const {
        inverseTransform,
        x1,
        y1,
        width,
        height
      } = coords;
      const pageCanvas = this.#getPageCanvas();
      const imageX1 = Math.ceil(x1 * pageCanvas.width);
      const imageY1 = Math.ceil(y1 * pageCanvas.height);
      const imageX2 = Math.floor((x1 + width / this.#pageWidth) * pageCanvas.width);
      const imageY2 = Math.floor((y1 + height / this.#pageHeight) * pageCanvas.height);
      imgElement.width = imageX2 - imageX1;
      imgElement.height = imageY2 - imageY1;
      const ctx = imgElement.getContext("2d");
      ctx.setTransform(...inverseTransform);
      ctx.translate(-imageX1, -imageY1);
      ctx.drawImage(pageCanvas, 0, 0);
    });
    return container;
  }
  #createImagePlaceholder([x1, y1, x2, y2, x3, y3]) {
    const width = Math.hypot((x3 - x1) * this.#pageWidth, (y3 - y1) * this.#pageHeight);
    const height = Math.hypot((x2 - x1) * this.#pageWidth, (y2 - y1) * this.#pageHeight);
    if (width < this.#minSize || height < this.#minSize) {
      return null;
    }
    const transform = [(x3 - x1) * this.#pageWidth / width, (y3 - y1) * this.#pageHeight / width, (x2 - x1) * this.#pageWidth / height, (y2 - y1) * this.#pageHeight / height, 0, 0];
    const inverseTransform = Util.inverseTransform(transform);
    const imgElement = document.createElement("canvas");
    imgElement.className = "textLayerImagePlaceholder";
    imgElement.width = 0;
    imgElement.height = 0;
    Object.assign(imgElement.style, {
      opacity: 0,
      position: "absolute",
      left: percentage(x1),
      top: percentage(y1),
      width: percentage(width / this.#pageWidth),
      height: percentage(height / this.#pageHeight),
      transformOrigin: "0% 0%",
      transform: `matrix(${transform.join(",")})`
    });
    this.#coordinatesByElement.set(imgElement, {
      inverseTransform,
      width,
      height,
      x1,
      y1
    });
    return imgElement;
  }
}

;// ./src/pdf.js



















{
  globalThis._pdfjsTestingUtils = {
    HighlightOutliner: HighlightOutliner
  };
}
globalThis.pdfjsLib = {
  AbortException: AbortException,
  AnnotationEditorLayer: AnnotationEditorLayer,
  AnnotationEditorParamsType: AnnotationEditorParamsType,
  AnnotationEditorType: AnnotationEditorType,
  AnnotationEditorUIManager: AnnotationEditorUIManager,
  AnnotationLayer: AnnotationLayer,
  AnnotationMode: AnnotationMode,
  AnnotationType: AnnotationType,
  applyOpacity: applyOpacity,
  build: build,
  ColorPicker: ColorPicker,
  createValidAbsoluteUrl: createValidAbsoluteUrl,
  CSSConstants: CSSConstants,
  DOMSVGFactory: DOMSVGFactory,
  DrawLayer: DrawLayer,
  FeatureTest: FeatureTest,
  fetchData: fetchData,
  findContrastColor: findContrastColor,
  getDocument: getDocument,
  getFilenameFromUrl: getFilenameFromUrl,
  getPdfFilenameFromUrl: getPdfFilenameFromUrl,
  getRGB: getRGB,
  getRGBA: getRGBA,
  getUuid: getUuid,
  GlobalWorkerOptions: GlobalWorkerOptions,
  ImageKind: ImageKind,
  InvalidPDFException: InvalidPDFException,
  isDataScheme: isDataScheme,
  isPdfFile: isPdfFile,
  isValidExplicitDest: isValidExplicitDest,
  makeArr: makeArr,
  makeMap: makeMap,
  makeObj: makeObj,
  makeSet: makeSet,
  MathClamp: MathClamp,
  noContextMenu: noContextMenu,
  normalizeUnicode: normalizeUnicode,
  OPS: OPS,
  OutputScale: OutputScale,
  PasswordException: PasswordException,
  PasswordResponses: PasswordResponses,
  PDFDataRangeTransport: PDFDataRangeTransport,
  PDFDateString: PDFDateString,
  PDFWorker: PDFWorker,
  PermissionFlag: PermissionFlag,
  PixelsPerInch: PixelsPerInch,
  RenderingCancelledException: RenderingCancelledException,
  renderRichText: renderRichText,
  ResponseException: ResponseException,
  setLayerDimensions: setLayerDimensions,
  shadow: shadow,
  SignatureExtractor: SignatureExtractor,
  stopEvent: stopEvent,
  SupportedImageMimeTypes: SupportedImageMimeTypes,
  TextLayer: TextLayer,
  TextLayerImages: TextLayerImages,
  TouchManager: TouchManager,
  updateUrlHash: updateUrlHash,
  Util: Util,
  VerbosityLevel: VerbosityLevel,
  version: version,
  XfaLayer: XfaLayer
};

export { AbortException, AnnotationEditorLayer, AnnotationEditorParamsType, AnnotationEditorType, AnnotationEditorUIManager, AnnotationLayer, AnnotationMode, AnnotationType, CSSConstants, ColorPicker, DOMSVGFactory, DrawLayer, FeatureTest, GlobalWorkerOptions, ImageKind, InvalidPDFException, MathClamp, OPS, OutputScale, PDFDataRangeTransport, PDFDateString, PDFWorker, PasswordException, PasswordResponses, PermissionFlag, PixelsPerInch, RenderingCancelledException, ResponseException, SignatureExtractor, SupportedImageMimeTypes, TextLayer, TextLayerImages, TouchManager, Util, VerbosityLevel, XfaLayer, applyOpacity, build, createValidAbsoluteUrl, fetchData, findContrastColor, getDocument, getFilenameFromUrl, getPdfFilenameFromUrl, getRGB, getRGBA, getUuid, isDataScheme, isPdfFile, isValidExplicitDest, makeArr, makeMap, makeObj, makeSet, noContextMenu, normalizeUnicode, renderRichText, setLayerDimensions, shadow, stopEvent, updateUrlHash, version };

//# sourceMappingURL=pdf.mjs.map