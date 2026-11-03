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

;// ./web/ui_utils.js
const DEFAULT_SCALE_VALUE = "auto";
const DEFAULT_SCALE = 1.0;
const DEFAULT_SCALE_DELTA = 1.1;
const MIN_SCALE = 0.1;
const MAX_SCALE = 25.0;
const UNKNOWN_SCALE = 0;
const MAX_AUTO_SCALE = 1.25;
const SCROLLBAR_PADDING = 40;
const VERTICAL_PADDING = 5;
const PresentationModeState = {
  UNKNOWN: 0,
  NORMAL: 1,
  CHANGING: 2,
  FULLSCREEN: 3
};
const SidebarView = {
  UNKNOWN: -1,
  NONE: 0,
  THUMBS: 1,
  OUTLINE: 2,
  ATTACHMENTS: 3,
  LAYERS: 4
};
const TextLayerMode = {
  DISABLE: 0,
  ENABLE: 1,
  ENABLE_PERMISSIONS: 2
};
const ScrollMode = {
  UNKNOWN: -1,
  VERTICAL: 0,
  HORIZONTAL: 1,
  WRAPPED: 2,
  PAGE: 3
};
const SpreadMode = {
  UNKNOWN: -1,
  NONE: 0,
  ODD: 1,
  EVEN: 2
};
const CursorTool = {
  SELECT: 0,
  HAND: 1,
  ZOOM: 2
};
const AutoPrintRegExp = /\bprint\s*\(/;
function scrollIntoView(element, spot) {
  let parent = element.offsetParent;
  if (!parent) {
    console.error("offsetParent is not set -- cannot scroll");
    return;
  }
  let offsetY = element.offsetTop + element.clientTop;
  let offsetX = element.offsetLeft + element.clientLeft;
  while (parent.clientHeight === parent.scrollHeight && parent.clientWidth === parent.scrollWidth) {
    offsetY += parent.offsetTop;
    offsetX += parent.offsetLeft;
    parent = parent.offsetParent;
    if (!parent) {
      return;
    }
  }
  if (spot) {
    if (spot.top !== undefined) {
      offsetY += spot.top;
    }
    if (spot.left !== undefined) {
      offsetX += spot.left;
      parent.scrollLeft = offsetX;
    }
  }
  parent.scrollTop = offsetY;
}
function watchScroll(viewAreaElement, callback, abortSignal = undefined) {
  function onRAF() {
    rAF = null;
    const currentX = viewAreaElement.scrollLeft;
    const lastX = state.lastX;
    if (currentX !== lastX) {
      state.right = currentX > lastX;
    }
    state.lastX = currentX;
    const currentY = viewAreaElement.scrollTop;
    const lastY = state.lastY;
    if (currentY !== lastY) {
      state.down = currentY > lastY;
    }
    state.lastY = currentY;
    callback(state);
  }
  const state = {
    right: true,
    down: true,
    lastX: viewAreaElement.scrollLeft,
    lastY: viewAreaElement.scrollTop
  };
  let rAF = null;
  viewAreaElement.addEventListener("scroll", () => {
    rAF ??= window.requestAnimationFrame(onRAF);
  }, {
    useCapture: true,
    signal: abortSignal
  });
  abortSignal?.addEventListener("abort", () => window.cancelAnimationFrame(rAF), {
    once: true
  });
  return state;
}
function parseQueryString(query) {
  const params = new Map();
  for (const [key, value] of new URLSearchParams(query)) {
    params.set(key.toLowerCase(), value);
  }
  return params;
}
const InvisibleCharsRegExp = /[\x00-\x1F]/g;
function removeNullCharacters(str, replaceInvisible = false) {
  if (!InvisibleCharsRegExp.test(str)) {
    return str;
  }
  return replaceInvisible ? str.replaceAll(InvisibleCharsRegExp, m => m === "\x00" ? "" : " ") : str.replaceAll("\x00", "");
}
function binarySearchFirstItem(items, condition, start = 0) {
  let minIndex = start;
  let maxIndex = items.length - 1;
  if (maxIndex < 0 || !condition(items[maxIndex])) {
    return items.length;
  }
  if (condition(items[minIndex])) {
    return minIndex;
  }
  while (minIndex < maxIndex) {
    const currentIndex = minIndex + maxIndex >> 1;
    const currentItem = items[currentIndex];
    if (condition(currentItem)) {
      maxIndex = currentIndex;
    } else {
      minIndex = currentIndex + 1;
    }
  }
  return minIndex;
}
function approximateFraction(x) {
  if (Math.floor(x) === x) {
    return [x, 1];
  }
  const xinv = 1 / x;
  const limit = 8;
  if (xinv > limit) {
    return [1, limit];
  } else if (Math.floor(xinv) === xinv) {
    return [1, xinv];
  }
  const x_ = x > 1 ? xinv : x;
  let a = 0,
    b = 1,
    c = 1,
    d = 1;
  while (true) {
    const p = a + c,
      q = b + d;
    if (q > limit) {
      break;
    }
    if (x_ <= p / q) {
      c = p;
      d = q;
    } else {
      a = p;
      b = q;
    }
  }
  if (x_ - a / b < c / d - x_) {
    return x_ === x ? [a, b] : [b, a];
  }
  return x_ === x ? [c, d] : [d, c];
}
function floorToDivide(x, div) {
  return x - x % div;
}
function getPageSizeInches({
  view,
  userUnit,
  rotate
}) {
  const [x1, y1, x2, y2] = view;
  const changeOrientation = rotate % 180 !== 0;
  const width = (x2 - x1) / 72 * userUnit;
  const height = (y2 - y1) / 72 * userUnit;
  return {
    width: changeOrientation ? height : width,
    height: changeOrientation ? width : height
  };
}
function backtrackBeforeAllVisibleElements(index, views, top) {
  if (index < 2) {
    return index;
  }
  let elt = views[index].div;
  let pageTop = elt.offsetTop + elt.clientTop;
  if (pageTop >= top) {
    elt = views[index - 1].div;
    pageTop = elt.offsetTop + elt.clientTop;
  }
  for (let i = index - 2; i >= 0; --i) {
    elt = views[i].div;
    if (elt.offsetTop + elt.clientTop + elt.clientHeight <= pageTop) {
      break;
    }
    index = i;
  }
  return index;
}
function visibleSort(a, b) {
  const pc = a.percent - b.percent;
  return Math.abs(pc) > 0.001 ? -pc : a.id - b.id;
}
function getVisibleElements({
  scrollEl,
  views,
  sortByVisibility = false,
  horizontal = false,
  rtl = false
}) {
  const top = scrollEl.scrollTop,
    bottom = top + scrollEl.clientHeight;
  const left = scrollEl.scrollLeft,
    right = left + scrollEl.clientWidth;
  function isElementBottomAfterViewTop(view) {
    const element = view.div;
    const elementBottom = element.offsetTop + element.clientTop + element.clientHeight;
    return elementBottom > top;
  }
  function isElementNextAfterViewHorizontally(view) {
    const element = view.div;
    const elementLeft = element.offsetLeft + element.clientLeft;
    const elementRight = elementLeft + element.clientWidth;
    return rtl ? elementLeft < right : elementRight > left;
  }
  const visible = [],
    ids = new Set(),
    numViews = views.length;
  let firstVisibleElementInd = binarySearchFirstItem(views, horizontal ? isElementNextAfterViewHorizontally : isElementBottomAfterViewTop);
  if (firstVisibleElementInd > 0 && firstVisibleElementInd < numViews && !horizontal) {
    firstVisibleElementInd = backtrackBeforeAllVisibleElements(firstVisibleElementInd, views, top);
  }
  let lastEdge = horizontal ? right : -1;
  for (let i = firstVisibleElementInd; i < numViews; i++) {
    const view = views[i],
      element = view.div;
    const currentWidth = element.offsetLeft + element.clientLeft;
    const currentHeight = element.offsetTop + element.clientTop;
    const viewWidth = element.clientWidth,
      viewHeight = element.clientHeight;
    const viewRight = currentWidth + viewWidth;
    const viewBottom = currentHeight + viewHeight;
    if (lastEdge === -1) {
      if (viewBottom >= bottom) {
        lastEdge = viewBottom;
      }
    } else if ((horizontal ? currentWidth : currentHeight) > lastEdge) {
      break;
    }
    if (viewBottom <= top || currentHeight >= bottom || viewRight <= left || currentWidth >= right) {
      continue;
    }
    const minY = Math.max(0, top - currentHeight);
    const minX = Math.max(0, left - currentWidth);
    const hiddenHeight = minY + Math.max(0, viewBottom - bottom);
    const hiddenWidth = minX + Math.max(0, viewRight - right);
    const fractionHeight = (viewHeight - hiddenHeight) / viewHeight,
      fractionWidth = (viewWidth - hiddenWidth) / viewWidth;
    const percent = fractionHeight * fractionWidth * 100 | 0;
    visible.push({
      id: view.id,
      x: currentWidth,
      y: currentHeight,
      visibleArea: percent === 100 ? null : {
        minX,
        minY,
        maxX: Math.min(viewRight, right) - currentWidth,
        maxY: Math.min(viewBottom, bottom) - currentHeight
      },
      view,
      percent,
      widthPercent: fractionWidth * 100 | 0
    });
    ids.add(view.id);
  }
  const first = visible[0],
    last = visible.at(-1);
  if (sortByVisibility) {
    visible.sort(visibleSort);
  }
  return {
    first,
    last,
    views: visible,
    ids
  };
}
function normalizeWheelEventDirection(evt) {
  let delta = Math.hypot(evt.deltaX, evt.deltaY);
  const angle = Math.atan2(evt.deltaY, evt.deltaX);
  if (-0.25 * Math.PI < angle && angle < 0.75 * Math.PI) {
    delta = -delta;
  }
  return delta;
}
function normalizeWheelEventDelta(evt) {
  const deltaMode = evt.deltaMode;
  let delta = normalizeWheelEventDirection(evt);
  const MOUSE_PIXELS_PER_LINE = 30;
  const MOUSE_LINES_PER_PAGE = 30;
  if (deltaMode === WheelEvent.DOM_DELTA_PIXEL) {
    delta /= MOUSE_PIXELS_PER_LINE * MOUSE_LINES_PER_PAGE;
  } else if (deltaMode === WheelEvent.DOM_DELTA_LINE) {
    delta /= MOUSE_LINES_PER_PAGE;
  }
  return delta;
}
function isValidRotation(angle) {
  return Number.isInteger(angle) && angle % 90 === 0;
}
function isValidScrollMode(mode) {
  return Number.isInteger(mode) && Object.values(ScrollMode).includes(mode) && mode !== ScrollMode.UNKNOWN;
}
function isValidSpreadMode(mode) {
  return Number.isInteger(mode) && Object.values(SpreadMode).includes(mode) && mode !== SpreadMode.UNKNOWN;
}
function isPortraitOrientation(size) {
  return size.width <= size.height;
}
const animationStarted = new Promise(function (resolve) {
  window.requestAnimationFrame(resolve);
});
const docStyle = document.documentElement.style;
class ProgressBar {
  #classList = null;
  #disableAutoFetchTimeout = null;
  #percent = 0;
  #style = null;
  #visible = true;
  constructor(bar) {
    this.#classList = bar.classList;
    this.#style = bar.style;
  }
  get percent() {
    return this.#percent;
  }
  set percent(val) {
    this.#percent = val;
    if (isNaN(val)) {
      this.#classList.add("indeterminate");
      return;
    }
    this.#classList.remove("indeterminate");
    this.#style.setProperty("--progressBar-percent", `${this.#percent}%`);
  }
  setWidth(viewer) {
    if (!viewer) {
      return;
    }
    const container = viewer.parentNode;
    const scrollbarWidth = container.offsetWidth - viewer.offsetWidth;
    if (scrollbarWidth > 0) {
      this.#style.setProperty("--progressBar-end-offset", `${scrollbarWidth}px`);
    }
  }
  setDisableAutoFetch(delay = 5000) {
    if (this.#percent === 100 || isNaN(this.#percent)) {
      return;
    }
    if (this.#disableAutoFetchTimeout) {
      clearTimeout(this.#disableAutoFetchTimeout);
    }
    this.show();
    this.#disableAutoFetchTimeout = setTimeout(() => {
      this.#disableAutoFetchTimeout = null;
      this.hide();
    }, delay);
  }
  hide() {
    if (!this.#visible) {
      return;
    }
    this.#visible = false;
    this.#classList.add("hidden");
  }
  show() {
    if (this.#visible) {
      return;
    }
    this.#visible = true;
    this.#classList.remove("hidden");
  }
}
function getActiveOrFocusedElement() {
  let curRoot = document;
  let curActiveOrFocused = curRoot.activeElement || curRoot.querySelector(":focus");
  while (curActiveOrFocused?.shadowRoot) {
    curRoot = curActiveOrFocused.shadowRoot;
    curActiveOrFocused = curRoot.activeElement || curRoot.querySelector(":focus");
  }
  return curActiveOrFocused;
}
function apiPageLayoutToViewerModes(layout) {
  let scrollMode = ScrollMode.VERTICAL,
    spreadMode = SpreadMode.NONE;
  switch (layout) {
    case "SinglePage":
      scrollMode = ScrollMode.PAGE;
      break;
    case "OneColumn":
      break;
    case "TwoPageLeft":
      scrollMode = ScrollMode.PAGE;
    case "TwoColumnLeft":
      spreadMode = SpreadMode.ODD;
      break;
    case "TwoPageRight":
      scrollMode = ScrollMode.PAGE;
    case "TwoColumnRight":
      spreadMode = SpreadMode.EVEN;
      break;
  }
  return {
    scrollMode,
    spreadMode
  };
}
function apiPageModeToSidebarView(mode) {
  switch (mode) {
    case "UseNone":
      return SidebarView.NONE;
    case "UseThumbs":
      return SidebarView.THUMBS;
    case "UseOutlines":
      return SidebarView.OUTLINE;
    case "UseAttachments":
      return SidebarView.ATTACHMENTS;
    case "UseOC":
      return SidebarView.LAYERS;
  }
  return SidebarView.NONE;
}
function toggleCheckedBtn(button, toggle, view = null) {
  button.classList.toggle("toggled", toggle);
  button.setAttribute("aria-checked", toggle);
  view?.classList.toggle("hidden", !toggle);
}
function toggleSelectedBtn(button, toggle, view = null) {
  button.classList.toggle("selected", toggle);
  button.setAttribute("aria-selected", toggle);
  view?.classList.toggle("hidden", !toggle);
}
function toggleExpandedBtn(button, toggle, view = null) {
  button.classList.toggle("toggled", toggle);
  button.setAttribute("aria-expanded", toggle);
  view?.classList.toggle("hidden", !toggle);
}
const calcRound = function () {
  const e = document.createElement("div");
  e.style.width = "round(down, calc(1.6666666666666665 * 792px), 1px)";
  return e.style.width === "calc(1320px)" ? Math.fround : x => x;
}();

;// ./web/app_options.js
{
  var compatParams = new Map();
  const {
    maxTouchPoints,
    platform,
    userAgent
  } = navigator;
  const isAndroid = /Android/.test(userAgent);
  const isIOS = /\b(?:iPad|iPhone|iPod)(?=;)/.test(userAgent) || platform === "MacIntel" && maxTouchPoints > 1;
  if (isIOS || isAndroid) {
    compatParams.set("maxCanvasPixels", 5242880);
  }
  if (isAndroid) {
    compatParams.set("useSystemFonts", false);
  }
}
const OptionKind = {
  BROWSER: 0x01,
  VIEWER: 0x02,
  API: 0x04,
  WORKER: 0x08,
  EVENT_DISPATCH: 0x10,
  PREFERENCE: 0x80
};
const Type = {
  BOOLEAN: 0x01,
  NUMBER: 0x02,
  OBJECT: 0x04,
  STRING: 0x08,
  UNDEFINED: 0x10
};
const defaultOptions = new Map([["allowedGlobalEvents", {
  value: null,
  kind: OptionKind.BROWSER
}], ["canvasMaxAreaInBytes", {
  value: -1,
  kind: OptionKind.BROWSER + OptionKind.API
}], ["isInAutomation", {
  value: false,
  kind: OptionKind.BROWSER
}], ["localeProperties", {
  value: {
    lang: navigator.language || "en-US"
  },
  kind: OptionKind.BROWSER
}], ["maxCanvasDim", {
  value: 32767,
  kind: OptionKind.BROWSER + OptionKind.VIEWER
}], ["nimbusDataStr", {
  value: "",
  kind: OptionKind.BROWSER
}], ["supportsCaretBrowsingMode", {
  value: false,
  kind: OptionKind.BROWSER
}], ["supportsDocumentFonts", {
  value: true,
  kind: OptionKind.BROWSER
}], ["supportsDownloading", {
  value: true,
  kind: OptionKind.BROWSER
}], ["supportsIntegratedFind", {
  value: false,
  kind: OptionKind.BROWSER
}], ["supportsMouseWheelZoomCtrlKey", {
  value: true,
  kind: OptionKind.BROWSER
}], ["supportsMouseWheelZoomMetaKey", {
  value: true,
  kind: OptionKind.BROWSER
}], ["supportsPinchToZoom", {
  value: true,
  kind: OptionKind.BROWSER
}], ["supportsPrinting", {
  value: true,
  kind: OptionKind.BROWSER
}], ["toolbarDensity", {
  value: 0,
  kind: OptionKind.BROWSER + OptionKind.EVENT_DISPATCH
}], ["altTextLearnMoreUrl", {
  value: "",
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["annotationEditorMode", {
  value: 0,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["annotationMode", {
  value: 2,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["capCanvasAreaFactor", {
  value: 200,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["commentLearnMoreUrl", {
  value: "",
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["cursorToolOnLoad", {
  value: 0,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["debuggerSrc", {
  value: "./debugger.mjs",
  kind: OptionKind.VIEWER
}], ...[["defaultUrl", {
  value: "compressed.tracemonkey-pldi-09.pdf",
  kind: OptionKind.VIEWER
}]], ["defaultZoomDelay", {
  value: 400,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["defaultZoomValue", {
  value: "",
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["disableHistory", {
  value: false,
  kind: OptionKind.VIEWER
}], ["disablePageLabels", {
  value: false,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ...[["disablePreferences", {
  value: false,
  kind: OptionKind.VIEWER
}]], ...[], ["enableAltText", {
  value: false,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["enableAltTextModelDownload", {
  value: true,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE + OptionKind.EVENT_DISPATCH
}], ["enableAutoLinking", {
  value: true,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["enableComment", {
  value: false,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["enableDetailCanvas", {
  value: true,
  kind: OptionKind.VIEWER
}], ...[], ["enableGuessAltText", {
  value: true,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE + OptionKind.EVENT_DISPATCH
}], ["enableHighlightFloatingButton", {
  value: false,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["enableMerge", {
  value: false,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["enableNewAltTextWhenAddingImage", {
  value: true,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["enableNewBadge", {
  value: false,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["enableNova", {
  value: true,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["enableOptimizedPartialRendering", {
  value: false,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["enablePermissions", {
  value: false,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["enablePrintAutoRotate", {
  value: true,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["enableScripting", {
  value: true,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["enableSelectionRendering", {
  value: true,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["enableSignatureEditor", {
  value: false,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["enableSignatureVerification", {
  value: false,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["enableSplitMerge", {
  value: false,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["enableUpdatedAddImage", {
  value: false,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["externalLinkRel", {
  value: "noopener noreferrer nofollow",
  kind: OptionKind.VIEWER
}], ["externalLinkTarget", {
  value: 0,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ...[], ["highlightEditorColors", {
  value: "yellow=#FFFF98,green=#53FFBC,blue=#80EBFF,pink=#FFCBE6,red=#FF4F5F," + "yellow_HCM=#FFFFCC,green_HCM=#53FFBC,blue_HCM=#80EBFF,pink_HCM=#F6B8FF,red_HCM=#C50043",
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["historyUpdateUrl", {
  value: false,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["ignoreDestinationZoom", {
  value: false,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["imageResourcesPath", {
  value: "./images/",
  kind: OptionKind.VIEWER
}], ["imagesRightClickMinSize", {
  value: -1,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["maxCanvasPixels", {
  value: 2 ** 25,
  kind: OptionKind.VIEWER
}], ["minDurationToUpdateCanvas", {
  value: 500,
  kind: OptionKind.VIEWER
}], ["forcePageColors", {
  value: false,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["pageColorsBackground", {
  value: "Canvas",
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["pageColorsForeground", {
  value: "CanvasText",
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["pdfBugEnabled", {
  value: false,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["postMessageAfterPrintCallback", {
  value: false,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["printResolution", {
  value: 150,
  kind: OptionKind.VIEWER
}], ...[], ...[["sandboxBundleSrc", {
  value: "../build/pdf.sandbox.mjs",
  kind: OptionKind.VIEWER
}]], ["sidebarViewOnLoad", {
  value: -1,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["scrollModeOnLoad", {
  value: -1,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["spreadModeOnLoad", {
  value: -1,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["textLayerMode", {
  value: 1,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["viewerCssTheme", {
  value: 0,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["viewOnLoad", {
  value: 0,
  kind: OptionKind.VIEWER + OptionKind.PREFERENCE
}], ["cMapPacked", {
  value: true,
  kind: OptionKind.API
}], ["cMapUrl", {
  value: "../web/cmaps/",
  kind: OptionKind.API
}], ["disableAutoFetch", {
  value: false,
  kind: OptionKind.API + OptionKind.PREFERENCE
}], ["disableFontFace", {
  value: false,
  kind: OptionKind.API + OptionKind.PREFERENCE
}], ["disableRange", {
  value: false,
  kind: OptionKind.API + OptionKind.PREFERENCE
}], ["disableStream", {
  value: false,
  kind: OptionKind.API + OptionKind.PREFERENCE
}], ["disableWorkerRendering", {
  value: true,
  kind: OptionKind.API + OptionKind.PREFERENCE
}], ["docBaseUrl", {
  value: "",
  kind: OptionKind.API
}], ["enableHWA", {
  value: true,
  kind: OptionKind.API + OptionKind.PREFERENCE
}], ["enableWebGPU", {
  value: true,
  kind: OptionKind.API + OptionKind.PREFERENCE
}], ["enableXfa", {
  value: true,
  kind: OptionKind.API + OptionKind.PREFERENCE
}], ["fontExtraProperties", {
  value: false,
  kind: OptionKind.API
}], ["iccUrl", {
  value: "../web/iccs/",
  kind: OptionKind.API
}], ["isOffscreenCanvasSupported", {
  value: true,
  kind: OptionKind.API
}], ["maxImageSize", {
  value: -1,
  kind: OptionKind.API
}], ["pdfBug", {
  value: false,
  kind: OptionKind.API
}], ["standardFontDataUrl", {
  value: "../web/standard_fonts/",
  kind: OptionKind.API
}], ["useSystemFonts", {
  value: undefined,
  kind: OptionKind.API,
  type: Type.BOOLEAN + Type.UNDEFINED
}], ["verbosity", {
  value: 1,
  kind: OptionKind.API
}], ["wasmUrl", {
  value: "../web/wasm/",
  kind: OptionKind.API
}], ["rendererPorts", {
  value: [],
  kind: OptionKind.WORKER
}], ["rendererSrc", {
  value: "../build/pdf.renderer.mjs",
  kind: OptionKind.WORKER
}], ["workerPort", {
  value: null,
  kind: OptionKind.WORKER
}], ["workerSrc", {
  value: "../build/pdf.worker.mjs",
  kind: OptionKind.WORKER
}]]);
class AppOptions {
  static eventBus;
  static #opts = new Map();
  static {
    for (const [name, defaultOpt] of defaultOptions) {
      this.#opts.set(name, defaultOpt.value);
    }
    for (const [name, value] of compatParams) {
      this.#opts.set(name, value);
    }
    this._hasInvokedSet = false;
    this._checkDisablePreferences = () => {
      if (this.get("disablePreferences")) {
        return true;
      }
      if (this._hasInvokedSet) {
        console.warn("The Preferences may override manually set AppOptions; " + 'please use the "disablePreferences"-option to prevent that.');
      }
      return false;
    };
  }
  static get(name) {
    return this.#opts.get(name);
  }
  static getAll(kind = null, defaultOnly = false) {
    const options = Object.create(null);
    for (const [name, defaultOpt] of defaultOptions) {
      if (kind && !(kind & defaultOpt.kind)) {
        continue;
      }
      options[name] = !defaultOnly ? this.#opts.get(name) : defaultOpt.value;
    }
    return options;
  }
  static set(name, value) {
    this.setAll({
      [name]: value
    });
  }
  static setAll(options, prefs = false) {
    this._hasInvokedSet ||= true;
    let events;
    for (const name in options) {
      const defaultOpt = defaultOptions.get(name),
        userOpt = options[name];
      if (!defaultOpt || !(typeof userOpt === typeof defaultOpt.value || Type[(typeof userOpt).toUpperCase()] & defaultOpt.type)) {
        continue;
      }
      const {
        kind
      } = defaultOpt;
      if (prefs && !(kind & OptionKind.BROWSER || kind & OptionKind.PREFERENCE)) {
        continue;
      }
      if (this.eventBus && kind & OptionKind.EVENT_DISPATCH) {
        (events ??= new Map()).set(name, userOpt);
      }
      this.#opts.set(name, userOpt);
    }
    events?.forEach((value, name) => {
      this.eventBus.dispatch(name.toLowerCase(), {
        source: this,
        value
      });
    });
  }
}

;// ./web/pdfjs.js
const {
  AbortException,
  AnnotationEditorLayer,
  AnnotationEditorParamsType,
  AnnotationEditorType,
  AnnotationEditorUIManager,
  AnnotationLayer,
  AnnotationMode,
  AnnotationType,
  applyOpacity,
  build,
  ColorPicker,
  createValidAbsoluteUrl,
  CSSConstants,
  DOMSVGFactory,
  DrawLayer,
  FeatureTest,
  fetchData,
  findContrastColor,
  getDocument,
  getFilenameFromUrl,
  getPdfFilenameFromUrl,
  getRGB,
  getRGBA,
  getUuid,
  GlobalWorkerOptions,
  ImageKind,
  InvalidPDFException,
  isDataScheme,
  isPdfFile,
  isValidExplicitDest,
  makeArr,
  makeMap,
  makeObj,
  makeSet,
  MathClamp,
  noContextMenu,
  normalizeUnicode,
  OPS,
  OutputScale,
  PasswordException,
  PasswordResponses,
  PDFDataRangeTransport,
  PDFDateString,
  PDFWorker,
  PermissionFlag,
  PixelsPerInch,
  RenderingCancelledException,
  renderRichText,
  ResponseException,
  setLayerDimensions,
  shadow,
  SignatureExtractor,
  stopEvent,
  SupportedImageMimeTypes,
  TextLayer,
  TextLayerImages,
  TouchManager,
  updateUrlHash,
  Util,
  VerbosityLevel,
  version,
  XfaLayer
} = globalThis.pdfjsLib;

;// ./web/internal_evt.js
const INTERNAL_EVT = "da0de832-0602-4da0-9ece-da36fcb1e1e0";
const internalOpt = Object.freeze({
  internal: INTERNAL_EVT
});

;// ./web/pdf_link_service.js



const DEFAULT_LINK_REL = "noopener noreferrer nofollow";
const LinkTarget = {
  NONE: 0,
  SELF: 1,
  BLANK: 2,
  PARENT: 3,
  TOP: 4
};
class PDFLinkService {
  externalLinkEnabled = true;
  constructor({
    eventBus,
    externalLinkTarget = null,
    externalLinkRel = null,
    ignoreDestinationZoom = false
  } = {}) {
    this.eventBus = eventBus;
    this.externalLinkTarget = externalLinkTarget;
    this.externalLinkRel = externalLinkRel;
    this._ignoreDestinationZoom = ignoreDestinationZoom;
    this.baseUrl = null;
    this.pdfDocument = null;
    this.pdfViewer = null;
    this.pdfHistory = null;
  }
  setDocument(pdfDocument, baseUrl = null) {
    this.baseUrl = baseUrl;
    this.pdfDocument = pdfDocument;
  }
  setViewer(pdfViewer) {
    this.pdfViewer = pdfViewer;
  }
  setHistory(pdfHistory) {
    this.pdfHistory = pdfHistory;
  }
  get pagesCount() {
    return this.pdfDocument?.pagesMapper.pagesNumber || 0;
  }
  get page() {
    return this.pdfDocument ? this.pdfViewer.currentPageNumber : 1;
  }
  set page(value) {
    if (this.pdfDocument) {
      this.pdfViewer.currentPageNumber = value;
    }
  }
  get rotation() {
    return this.pdfDocument ? this.pdfViewer.pagesRotation : 0;
  }
  set rotation(value) {
    if (this.pdfDocument) {
      this.pdfViewer.pagesRotation = value;
    }
  }
  get isInPresentationMode() {
    return this.pdfDocument ? this.pdfViewer.isInPresentationMode : false;
  }
  async goToDestination(dest) {
    if (!this.pdfDocument) {
      return;
    }
    let namedDest, explicitDest, pageNumber;
    if (typeof dest === "string") {
      namedDest = dest;
      explicitDest = await this.pdfDocument.getDestination(dest);
    } else {
      namedDest = null;
      explicitDest = await dest;
    }
    if (!Array.isArray(explicitDest)) {
      console.error(`goToDestination: "${explicitDest}" is not a valid destination array, for dest="${dest}".`);
      return;
    }
    const [destRef] = explicitDest;
    if (destRef && typeof destRef === "object") {
      pageNumber = this.pdfDocument.cachedPageNumber(destRef);
      if (!pageNumber) {
        try {
          pageNumber = (await this.pdfDocument.getPageIndex(destRef)) + 1;
        } catch {
          console.error(`goToDestination: "${destRef}" is not a valid page reference, for dest="${dest}".`);
          return;
        }
      }
    } else if (Number.isInteger(destRef)) {
      pageNumber = destRef + 1;
    }
    if (!pageNumber || pageNumber < 1 || pageNumber > this.pagesCount) {
      console.error(`goToDestination: "${pageNumber}" is not a valid page number, for dest="${dest}".`);
      return;
    }
    if (this.pdfHistory) {
      this.pdfHistory.pushCurrentPosition();
      this.pdfHistory.push({
        namedDest,
        explicitDest,
        pageNumber
      });
    }
    this.pdfViewer.scrollPageIntoView({
      pageNumber,
      destArray: explicitDest,
      ignoreDestinationZoom: this._ignoreDestinationZoom
    });
    const ac = new AbortController();
    this.eventBus.on("textlayerrendered", evt => {
      if (evt.pageNumber === pageNumber) {
        evt.source.textLayer.div.focus();
        ac.abort();
      }
    }, {
      signal: ac.signal,
      ...internalOpt
    });
  }
  goToPage(val) {
    if (!this.pdfDocument) {
      return;
    }
    const pageNumber = typeof val === "string" && this.pdfViewer.pageLabelToPageNumber(val) || val | 0;
    if (!(Number.isInteger(pageNumber) && pageNumber > 0 && pageNumber <= this.pagesCount)) {
      console.error(`PDFLinkService.goToPage: "${val}" is not a valid page.`);
      return;
    }
    if (this.pdfHistory) {
      this.pdfHistory.pushCurrentPosition();
      this.pdfHistory.pushPage(pageNumber);
    }
    this.pdfViewer.scrollPageIntoView({
      pageNumber
    });
  }
  goToXY(pageNumber, x, y, options = {}) {
    this.pdfViewer.scrollPageIntoView({
      pageNumber,
      destArray: [null, {
        name: "XYZ"
      }, x, y],
      ignoreDestinationZoom: true,
      ...options
    });
  }
  async getAttachmentContent(id) {
    try {
      return await this.pdfDocument?.getAttachmentContent(id);
    } catch (error) {
      if (!(error instanceof PasswordException)) {
        console.warn(`Unable to load attachment content: ${error}`);
      }
    }
    return null;
  }
  addLinkAttributes(link, url, newWindow = false) {
    if (!url || typeof url !== "string") {
      throw new Error('A valid "url" parameter must provided.');
    }
    const target = newWindow ? LinkTarget.BLANK : this.externalLinkTarget,
      rel = this.externalLinkRel;
    let displayUrl = url;
    const parsedUrl = URL.parse(url);
    if (parsedUrl?.username || parsedUrl?.password) {
      parsedUrl.username = parsedUrl.password = "";
      displayUrl = parsedUrl.href;
    }
    if (this.externalLinkEnabled) {
      link.href = url;
      link.title = displayUrl;
    } else {
      link.href = "";
      link.title = `Disabled: ${displayUrl}`;
      link.onclick = () => false;
    }
    let targetStr = "";
    switch (target) {
      case LinkTarget.NONE:
        break;
      case LinkTarget.SELF:
        targetStr = "_self";
        break;
      case LinkTarget.BLANK:
        targetStr = "_blank";
        break;
      case LinkTarget.PARENT:
        targetStr = "_parent";
        break;
      case LinkTarget.TOP:
        targetStr = "_top";
        break;
    }
    link.target = targetStr;
    link.rel = typeof rel === "string" ? rel : DEFAULT_LINK_REL;
  }
  getDestinationHash(dest) {
    if (typeof dest === "string") {
      if (dest.length > 0) {
        return this.getAnchorUrl("#" + escape(dest));
      }
    } else if (Array.isArray(dest)) {
      const str = JSON.stringify(dest);
      if (str.length > 0) {
        return this.getAnchorUrl("#" + escape(str));
      }
    }
    return this.getAnchorUrl("");
  }
  getAnchorUrl(anchor) {
    return this.baseUrl ? this.baseUrl + anchor : anchor;
  }
  setHash(hash) {
    if (!this.pdfDocument) {
      return;
    }
    let pageNumber, dest;
    if (hash.includes("=")) {
      const params = parseQueryString(hash);
      if (params.has("search")) {
        const query = params.get("search").replaceAll('"', ""),
          phrase = params.get("phrase") === "true";
        this.eventBus.dispatch("findfromurlhash", {
          source: this,
          query: phrase ? query : query.match(/\S+/g)
        });
      }
      if (params.has("page")) {
        pageNumber = params.get("page") | 0 || 1;
      }
      if (params.has("zoom")) {
        const zoomArgs = params.get("zoom").split(",");
        const zoomArg = zoomArgs[0];
        const zoomArgNumber = parseFloat(zoomArg);
        if (!zoomArg.includes("Fit")) {
          dest = [null, {
            name: "XYZ"
          }, zoomArgs.length > 1 ? zoomArgs[1] | 0 : null, zoomArgs.length > 2 ? zoomArgs[2] | 0 : null, zoomArgNumber ? zoomArgNumber / 100 : zoomArg];
        } else if (zoomArg === "Fit" || zoomArg === "FitB") {
          dest = [null, {
            name: zoomArg
          }];
        } else if (zoomArg === "FitH" || zoomArg === "FitBH" || zoomArg === "FitV" || zoomArg === "FitBV") {
          dest = [null, {
            name: zoomArg
          }, zoomArgs.length > 1 ? zoomArgs[1] | 0 : null];
        } else if (zoomArg === "FitR") {
          if (zoomArgs.length !== 5) {
            console.error('PDFLinkService.setHash: Not enough parameters for "FitR".');
          } else {
            dest = [null, {
              name: zoomArg
            }, zoomArgs[1] | 0, zoomArgs[2] | 0, zoomArgs[3] | 0, zoomArgs[4] | 0];
          }
        } else {
          console.error(`PDFLinkService.setHash: "${zoomArg}" is not a valid zoom value.`);
        }
      }
      if (dest) {
        this.pdfViewer.scrollPageIntoView({
          pageNumber: pageNumber || this.page,
          destArray: dest,
          allowNegativeOffset: true
        });
      } else if (pageNumber) {
        this.page = pageNumber;
      }
      if (params.has("pagemode")) {
        this.eventBus.dispatch("pagemode", {
          source: this,
          mode: params.get("pagemode")
        });
      }
      if (params.has("nameddest")) {
        this.goToDestination(params.get("nameddest"));
      }
      return;
    }
    dest = unescape(hash);
    try {
      dest = JSON.parse(dest);
      if (!Array.isArray(dest)) {
        dest = dest.toString();
      }
    } catch {}
    if (typeof dest === "string" || isValidExplicitDest(dest)) {
      this.goToDestination(dest);
      return;
    }
    console.error(`PDFLinkService.setHash: "${unescape(hash)}" is not a valid destination.`);
  }
  executeNamedAction(action) {
    if (!this.pdfDocument) {
      return;
    }
    switch (action) {
      case "GoBack":
        this.pdfHistory?.back();
        break;
      case "GoForward":
        this.pdfHistory?.forward();
        break;
      case "NextPage":
        this.pdfViewer.nextPage();
        break;
      case "PrevPage":
        this.pdfViewer.previousPage();
        break;
      case "LastPage":
        this.page = this.pagesCount;
        break;
      case "FirstPage":
        this.page = 1;
        break;
      default:
        break;
    }
    this.eventBus.dispatch("namedaction", {
      source: this,
      action
    });
  }
  async executeSetOCGState(action) {
    if (!this.pdfDocument) {
      return;
    }
    const pdfDocument = this.pdfDocument,
      optionalContentConfig = await this.pdfViewer.optionalContentConfigPromise;
    if (pdfDocument !== this.pdfDocument) {
      return;
    }
    optionalContentConfig.setOCGState(action);
    this.pdfViewer.optionalContentConfigPromise = Promise.resolve(optionalContentConfig);
  }
}
class SimpleLinkService extends PDFLinkService {
  setDocument(pdfDocument, baseUrl = null) {}
}

;// ./web/event_utils.js


const WaitOnType = {
  EVENT: "event",
  TIMEOUT: "timeout"
};
async function waitOnEventOrTimeout({
  target,
  name,
  delay = 0
}) {
  if (typeof target !== "object" || !(name && typeof name === "string") || !(Number.isInteger(delay) && delay >= 0)) {
    throw new Error("waitOnEventOrTimeout - invalid parameters.");
  }
  const {
    promise,
    resolve
  } = Promise.withResolvers();
  const ac = new AbortController();
  function handler(type) {
    ac.abort();
    clearTimeout(timeout);
    resolve(type);
  }
  const evtMethod = target instanceof EventBus ? "on" : "addEventListener";
  const evtOpts = target instanceof EventBus ? {
    signal: ac.signal,
    ...internalOpt
  } : {
    signal: ac.signal
  };
  target[evtMethod](name, handler.bind(null, WaitOnType.EVENT), evtOpts);
  const timeout = setTimeout(handler.bind(null, WaitOnType.TIMEOUT), delay);
  return promise;
}
class EventBus {
  #listeners = new Map();
  constructor() {
    Object.seal(this);
  }
  on(eventName, listener, options = null) {
    let rmAbort = null;
    if (options?.signal instanceof AbortSignal) {
      const {
        signal
      } = options;
      if (signal.aborted) {
        console.error("Cannot use an `aborted` signal.");
        return;
      }
      const onAbort = () => this.off(eventName, listener);
      rmAbort = () => signal.removeEventListener("abort", onAbort);
      signal.addEventListener("abort", onAbort);
    }
    this.#listeners.getOrInsertComputed(eventName, makeSet).add({
      listener,
      internal: options?.internal === INTERNAL_EVT,
      once: options?.once === true,
      rmAbort
    });
  }
  off(eventName, listener, options = null) {
    const eventListeners = this.#listeners.get(eventName);
    const evt = eventListeners?.keys().find(e => e.listener === listener);
    if (evt) {
      evt.rmAbort?.();
      eventListeners.delete(evt);
    }
  }
  dispatch(eventName, data) {
    const eventListeners = this.#listeners.get(eventName);
    if (!eventListeners?.size) {
      return;
    }
    let extListeners;
    for (const {
      listener,
      internal,
      once
    } of new Set(eventListeners)) {
      if (once) {
        this.off(eventName, listener);
      }
      if (!internal) {
        (extListeners ??= []).push(listener);
        continue;
      }
      listener(data);
    }
    if (extListeners) {
      for (const listener of extListeners) {
        listener(data);
      }
    }
  }
}
class FirefoxEventBus extends EventBus {
  #externalServices;
  #globalEventNames;
  #isInAutomation;
  constructor(globalEventNames, externalServices, isInAutomation) {
    super();
    this.#globalEventNames = globalEventNames;
    this.#externalServices = externalServices;
    this.#isInAutomation = isInAutomation;
  }
  dispatch(eventName, data) {
    throw new Error("Not implemented: FirefoxEventBus.dispatch");
  }
}

;// ./web/external_services.js
class BaseExternalServices {
  updateFindControlState(data) {}
  updateFindMatchesCount(data) {}
  initPassiveLoading() {}
  reportTelemetry(data) {}
  reportText(data) {}
  async createL10n() {
    throw new Error("Not implemented: createL10n");
  }
  createScripting() {
    throw new Error("Not implemented: createScripting");
  }
  createSignatureStorage() {
    throw new Error("Not implemented: createSignatureStorage");
  }
  createSignatureVerifier() {
    return null;
  }
  printToPDF = null;
  updateEditorStates(data) {
    throw new Error("Not implemented: updateEditorStates");
  }
  dispatchGlobalEvent(_event) {}
}

;// ./web/preferences.js

class BasePreferences {
  #defaults = Object.freeze(AppOptions.getAll(OptionKind.PREFERENCE, true));
  #initializedPromise = null;
  constructor() {
    this.#initializedPromise = this._readFromStorage(this.#defaults).then(({
      browserPrefs,
      prefs
    }) => {
      if (AppOptions._checkDisablePreferences()) {
        return;
      }
      AppOptions.setAll({
        ...browserPrefs,
        ...prefs
      }, true);
    });
  }
  async _writeToStorage(prefObj) {
    throw new Error("Not implemented: _writeToStorage");
  }
  async _readFromStorage(prefObj) {
    throw new Error("Not implemented: _readFromStorage");
  }
  async reset() {
    await this.#initializedPromise;
    AppOptions.setAll(this.#defaults, true);
    await this._writeToStorage(this.#defaults);
  }
  async set(name, value) {
    await this.#initializedPromise;
    AppOptions.setAll({
      [name]: value
    }, true);
    await this._writeToStorage(AppOptions.getAll(OptionKind.PREFERENCE));
  }
  async get(name) {
    await this.#initializedPromise;
    return AppOptions.get(name);
  }
  get defaults() {
    return this.#defaults;
  }
  get initializedPromise() {
    return this.#initializedPromise;
  }
}

;// ./node_modules/@fluent/bundle/esm/types.js
class FluentType {
  constructor(value) {
    this.value = value;
  }
  valueOf() {
    return this.value;
  }
}
class FluentNone extends FluentType {
  constructor(value = "???") {
    super(value);
  }
  toString(scope) {
    return `{${this.value}}`;
  }
}
class FluentNumber extends FluentType {
  constructor(value, opts = {}) {
    super(value);
    this.opts = opts;
  }
  toString(scope) {
    if (scope) {
      try {
        const nf = scope.memoizeIntlObject(Intl.NumberFormat, this.opts);
        return nf.format(this.value);
      } catch (err) {
        scope.reportError(err);
      }
    }
    return this.value.toString(10);
  }
}
class FluentDateTime extends FluentType {
  static supportsValue(value) {
    if (typeof value === "number") return true;
    if (value instanceof Date) return true;
    if (value instanceof FluentType) return FluentDateTime.supportsValue(value.valueOf());
    if ("Temporal" in globalThis) {
      const _Temporal = globalThis.Temporal;
      if (value instanceof _Temporal.Instant || value instanceof _Temporal.PlainDateTime || value instanceof _Temporal.PlainDate || value instanceof _Temporal.PlainMonthDay || value instanceof _Temporal.PlainTime || value instanceof _Temporal.PlainYearMonth) {
        return true;
      }
    }
    return false;
  }
  constructor(value, opts = {}) {
    if (value instanceof FluentDateTime) {
      opts = {
        ...value.opts,
        ...opts
      };
      value = value.value;
    } else if (value instanceof FluentType) {
      value = value.valueOf();
    }
    if (typeof value === "object" && "calendarId" in value && opts.calendar === undefined) {
      opts = {
        ...opts,
        calendar: value.calendarId
      };
    }
    super(value);
    this.opts = opts;
  }
  [Symbol.toPrimitive](hint) {
    return hint === "string" ? this.toString() : this.toNumber();
  }
  toNumber() {
    const value = this.value;
    if (typeof value === "number") return value;
    if (value instanceof Date) return value.getTime();
    if ("epochMilliseconds" in value) {
      return value.epochMilliseconds;
    }
    if ("toZonedDateTime" in value) {
      return value.toZonedDateTime("UTC").epochMilliseconds;
    }
    throw new TypeError("Unwrapping a non-number value as a number");
  }
  toString(scope) {
    if (scope) {
      try {
        const dtf = scope.memoizeIntlObject(Intl.DateTimeFormat, this.opts);
        return dtf.format(this.value);
      } catch (err) {
        scope.reportError(err);
      }
    }
    if (typeof this.value === "number" || this.value instanceof Date) {
      return new Date(this.value).toISOString();
    }
    return this.value.toString();
  }
}
;// ./node_modules/@fluent/bundle/esm/resolver.js

const MAX_PLACEABLES = 100;
const FSI = "\u2068";
const PDI = "\u2069";
function match(scope, selector, key) {
  if (key === selector) {
    return true;
  }
  if (key instanceof FluentNumber && selector instanceof FluentNumber && key.value === selector.value) {
    return true;
  }
  if (selector instanceof FluentNumber && typeof key === "string") {
    let category = scope.memoizeIntlObject(Intl.PluralRules, selector.opts).select(selector.value);
    if (key === category) {
      return true;
    }
  }
  return false;
}
function getDefault(scope, variants, star) {
  if (variants[star]) {
    return resolvePattern(scope, variants[star].value);
  }
  scope.reportError(new RangeError("No default"));
  return new FluentNone();
}
function getArguments(scope, args) {
  const positional = [];
  const named = Object.create(null);
  for (const arg of args) {
    if (arg.type === "narg") {
      named[arg.name] = resolveExpression(scope, arg.value);
    } else {
      positional.push(resolveExpression(scope, arg));
    }
  }
  return {
    positional,
    named
  };
}
function resolveExpression(scope, expr) {
  switch (expr.type) {
    case "str":
      return expr.value;
    case "num":
      return new FluentNumber(expr.value, {
        minimumFractionDigits: expr.precision
      });
    case "var":
      return resolveVariableReference(scope, expr);
    case "mesg":
      return resolveMessageReference(scope, expr);
    case "term":
      return resolveTermReference(scope, expr);
    case "func":
      return resolveFunctionReference(scope, expr);
    case "select":
      return resolveSelectExpression(scope, expr);
    default:
      return new FluentNone();
  }
}
function resolveVariableReference(scope, {
  name
}) {
  let arg;
  if (scope.params) {
    if (Object.prototype.hasOwnProperty.call(scope.params, name)) {
      arg = scope.params[name];
    } else {
      return new FluentNone(`$${name}`);
    }
  } else if (scope.args && Object.prototype.hasOwnProperty.call(scope.args, name)) {
    arg = scope.args[name];
  } else {
    scope.reportError(new ReferenceError(`Unknown variable: $${name}`));
    return new FluentNone(`$${name}`);
  }
  if (arg instanceof FluentType) {
    return arg;
  }
  switch (typeof arg) {
    case "string":
      return arg;
    case "number":
      return new FluentNumber(arg);
    case "object":
      if (FluentDateTime.supportsValue(arg)) {
        return new FluentDateTime(arg);
      }
    default:
      scope.reportError(new TypeError(`Variable type not supported: $${name}, ${typeof arg}`));
      return new FluentNone(`$${name}`);
  }
}
function resolveMessageReference(scope, {
  name,
  attr
}) {
  const message = scope.bundle._messages.get(name);
  if (!message) {
    scope.reportError(new ReferenceError(`Unknown message: ${name}`));
    return new FluentNone(name);
  }
  if (attr) {
    const attribute = message.attributes[attr];
    if (attribute) {
      return resolvePattern(scope, attribute);
    }
    scope.reportError(new ReferenceError(`Unknown attribute: ${attr}`));
    return new FluentNone(`${name}.${attr}`);
  }
  if (message.value) {
    return resolvePattern(scope, message.value);
  }
  scope.reportError(new ReferenceError(`No value: ${name}`));
  return new FluentNone(name);
}
function resolveTermReference(scope, {
  name,
  attr,
  args
}) {
  const id = `-${name}`;
  const term = scope.bundle._terms.get(id);
  if (!term) {
    scope.reportError(new ReferenceError(`Unknown term: ${id}`));
    return new FluentNone(id);
  }
  if (attr) {
    const attribute = term.attributes[attr];
    if (attribute) {
      scope.params = getArguments(scope, args).named;
      const resolved = resolvePattern(scope, attribute);
      scope.params = null;
      return resolved;
    }
    scope.reportError(new ReferenceError(`Unknown attribute: ${attr}`));
    return new FluentNone(`${id}.${attr}`);
  }
  scope.params = getArguments(scope, args).named;
  const resolved = resolvePattern(scope, term.value);
  scope.params = null;
  return resolved;
}
function resolveFunctionReference(scope, {
  name,
  args
}) {
  let func = scope.bundle._functions[name];
  if (!func) {
    scope.reportError(new ReferenceError(`Unknown function: ${name}()`));
    return new FluentNone(`${name}()`);
  }
  if (typeof func !== "function") {
    scope.reportError(new TypeError(`Function ${name}() is not callable`));
    return new FluentNone(`${name}()`);
  }
  try {
    let resolved = getArguments(scope, args);
    return func(resolved.positional, resolved.named);
  } catch (err) {
    scope.reportError(err);
    return new FluentNone(`${name}()`);
  }
}
function resolveSelectExpression(scope, {
  selector,
  variants,
  star
}) {
  let sel = resolveExpression(scope, selector);
  if (sel instanceof FluentNone) {
    return getDefault(scope, variants, star);
  }
  for (const variant of variants) {
    const key = resolveExpression(scope, variant.key);
    if (match(scope, sel, key)) {
      return resolvePattern(scope, variant.value);
    }
  }
  return getDefault(scope, variants, star);
}
function resolveComplexPattern(scope, ptn) {
  if (scope.dirty.has(ptn)) {
    scope.reportError(new RangeError("Cyclic reference"));
    return new FluentNone();
  }
  scope.dirty.add(ptn);
  const result = [];
  const useIsolating = scope.bundle._useIsolating && ptn.length > 1;
  for (const elem of ptn) {
    if (typeof elem === "string") {
      result.push(scope.bundle._transform(elem));
      continue;
    }
    scope.placeables++;
    if (scope.placeables > MAX_PLACEABLES) {
      scope.dirty.delete(ptn);
      throw new RangeError(`Too many placeables expanded: ${scope.placeables}, ` + `max allowed is ${MAX_PLACEABLES}`);
    }
    if (useIsolating) {
      result.push(FSI);
    }
    result.push(resolveExpression(scope, elem).toString(scope));
    if (useIsolating) {
      result.push(PDI);
    }
  }
  scope.dirty.delete(ptn);
  return result.join("");
}
function resolvePattern(scope, value) {
  if (typeof value === "string") {
    return scope.bundle._transform(value);
  }
  return resolveComplexPattern(scope, value);
}
;// ./node_modules/@fluent/bundle/esm/scope.js
class Scope {
  constructor(bundle, errors, args) {
    this.dirty = new WeakSet();
    this.params = null;
    this.placeables = 0;
    this.bundle = bundle;
    this.errors = errors;
    this.args = args;
  }
  reportError(error) {
    if (!this.errors || !(error instanceof Error)) {
      throw error;
    }
    this.errors.push(error);
  }
  memoizeIntlObject(ctor, opts) {
    let cache = this.bundle._intls.get(ctor);
    if (!cache) {
      cache = {};
      this.bundle._intls.set(ctor, cache);
    }
    let id = JSON.stringify(opts);
    if (!cache[id]) {
      cache[id] = new ctor(this.bundle.locales, opts);
    }
    return cache[id];
  }
}
;// ./node_modules/@fluent/bundle/esm/builtins.js

function values(opts, allowed) {
  const unwrapped = Object.create(null);
  for (const [name, opt] of Object.entries(opts)) {
    if (allowed.includes(name)) {
      unwrapped[name] = opt.valueOf();
    }
  }
  return unwrapped;
}
const NUMBER_ALLOWED = ["unitDisplay", "currencyDisplay", "useGrouping", "minimumIntegerDigits", "minimumFractionDigits", "maximumFractionDigits", "minimumSignificantDigits", "maximumSignificantDigits"];
function NUMBER(args, opts) {
  let arg = args[0];
  if (arg instanceof FluentNone) {
    return new FluentNone(`NUMBER(${arg.valueOf()})`);
  }
  if (arg instanceof FluentNumber) {
    return new FluentNumber(arg.valueOf(), {
      ...arg.opts,
      ...values(opts, NUMBER_ALLOWED)
    });
  }
  if (arg instanceof FluentDateTime) {
    return new FluentNumber(arg.toNumber(), {
      ...values(opts, NUMBER_ALLOWED)
    });
  }
  throw new TypeError("Invalid argument to NUMBER");
}
const DATETIME_ALLOWED = ["dateStyle", "timeStyle", "fractionalSecondDigits", "dayPeriod", "hour12", "weekday", "era", "year", "month", "day", "hour", "minute", "second", "timeZoneName"];
function DATETIME(args, opts) {
  let arg = args[0];
  if (arg instanceof FluentNone) {
    return new FluentNone(`DATETIME(${arg.valueOf()})`);
  }
  if (arg instanceof FluentDateTime || arg instanceof FluentNumber) {
    return new FluentDateTime(arg, values(opts, DATETIME_ALLOWED));
  }
  throw new TypeError("Invalid argument to DATETIME");
}
;// ./node_modules/@fluent/bundle/esm/memoizer.js
const cache = new Map();
function getMemoizerForLocale(locales) {
  const stringLocale = Array.isArray(locales) ? locales.join(" ") : locales;
  let memoizer = cache.get(stringLocale);
  if (memoizer === undefined) {
    memoizer = new Map();
    cache.set(stringLocale, memoizer);
  }
  return memoizer;
}
;// ./node_modules/@fluent/bundle/esm/bundle.js





class FluentBundle {
  constructor(locales, {
    functions,
    useIsolating = true,
    transform = v => v
  } = {}) {
    this._terms = new Map();
    this._messages = new Map();
    this.locales = Array.isArray(locales) ? locales : [locales];
    this._functions = {
      NUMBER: NUMBER,
      DATETIME: DATETIME,
      ...functions
    };
    this._useIsolating = useIsolating;
    this._transform = transform;
    this._intls = getMemoizerForLocale(locales);
  }
  hasMessage(id) {
    return this._messages.has(id);
  }
  getMessage(id) {
    return this._messages.get(id);
  }
  addResource(res, {
    allowOverrides = false
  } = {}) {
    const errors = [];
    for (let i = 0; i < res.body.length; i++) {
      let entry = res.body[i];
      if (entry.id.startsWith("-")) {
        if (allowOverrides === false && this._terms.has(entry.id)) {
          errors.push(new Error(`Attempt to override an existing term: "${entry.id}"`));
          continue;
        }
        this._terms.set(entry.id, entry);
      } else {
        if (allowOverrides === false && this._messages.has(entry.id)) {
          errors.push(new Error(`Attempt to override an existing message: "${entry.id}"`));
          continue;
        }
        this._messages.set(entry.id, entry);
      }
    }
    return errors;
  }
  formatPattern(pattern, args = null, errors = null) {
    if (typeof pattern === "string") {
      return this._transform(pattern);
    }
    let scope = new Scope(this, errors, args);
    try {
      let value = resolveComplexPattern(scope, pattern);
      return value.toString(scope);
    } catch (err) {
      if (scope.errors && err instanceof Error) {
        scope.errors.push(err);
        return new FluentNone().toString(scope);
      }
      throw err;
    }
  }
}
;// ./node_modules/@fluent/bundle/esm/resource.js
const RE_MESSAGE_START = /^(-?[a-zA-Z][\w-]*) *= */gm;
const RE_ATTRIBUTE_START = /\.([a-zA-Z][\w-]*) *= */y;
const RE_VARIANT_START = /\*?\[/y;
const RE_NUMBER_LITERAL = /(-?[0-9]+(?:\.([0-9]+))?)/y;
const RE_IDENTIFIER = /([a-zA-Z][\w-]*)/y;
const RE_REFERENCE = /([$-])?([a-zA-Z][\w-]*)(?:\.([a-zA-Z][\w-]*))?/y;
const RE_FUNCTION_NAME = /^[A-Z][A-Z0-9_-]*$/;
const RE_TEXT_RUN = /([^{}\n\r]+)/y;
const RE_STRING_RUN = /([^\\"\n\r]*)/y;
const RE_STRING_ESCAPE = /\\([\\"])/y;
const RE_UNICODE_ESCAPE = /\\u([a-fA-F0-9]{4})|\\U([a-fA-F0-9]{6})/y;
const RE_LEADING_NEWLINES = /^\n+/;
const RE_TRAILING_SPACES = / +$/;
const RE_BLANK_LINES = / *\r?\n/g;
const RE_INDENT = /( *)$/;
const TOKEN_BRACE_OPEN = /{\s*/y;
const TOKEN_BRACE_CLOSE = /\s*}/y;
const TOKEN_BRACKET_OPEN = /\[\s*/y;
const TOKEN_BRACKET_CLOSE = /\s*] */y;
const TOKEN_PAREN_OPEN = /\s*\(\s*/y;
const TOKEN_ARROW = /\s*->\s*/y;
const TOKEN_COLON = /\s*:\s*/y;
const TOKEN_COMMA = /\s*,?\s*/y;
const TOKEN_BLANK = /\s+/y;
class FluentResource {
  constructor(source) {
    this.body = [];
    RE_MESSAGE_START.lastIndex = 0;
    let cursor = 0;
    while (true) {
      let next = RE_MESSAGE_START.exec(source);
      if (next === null) {
        break;
      }
      cursor = RE_MESSAGE_START.lastIndex;
      try {
        this.body.push(parseMessage(next[1]));
      } catch (err) {
        if (err instanceof SyntaxError) {
          continue;
        }
        throw err;
      }
    }
    function test(re) {
      re.lastIndex = cursor;
      return re.test(source);
    }
    function consumeChar(char, errorClass) {
      if (source[cursor] === char) {
        cursor++;
        return true;
      }
      if (errorClass) {
        throw new errorClass(`Expected ${char}`);
      }
      return false;
    }
    function consumeToken(re, errorClass) {
      if (test(re)) {
        cursor = re.lastIndex;
        return true;
      }
      if (errorClass) {
        throw new errorClass(`Expected ${re.toString()}`);
      }
      return false;
    }
    function match(re) {
      re.lastIndex = cursor;
      let result = re.exec(source);
      if (result === null) {
        throw new SyntaxError(`Expected ${re.toString()}`);
      }
      cursor = re.lastIndex;
      return result;
    }
    function match1(re) {
      return match(re)[1];
    }
    function parseMessage(id) {
      let value = parsePattern();
      let attributes = parseAttributes();
      if (value === null && Object.keys(attributes).length === 0) {
        throw new SyntaxError("Expected message value or attributes");
      }
      return {
        id,
        value,
        attributes
      };
    }
    function parseAttributes() {
      let attrs = Object.create(null);
      while (test(RE_ATTRIBUTE_START)) {
        let name = match1(RE_ATTRIBUTE_START);
        let value = parsePattern();
        if (value === null) {
          throw new SyntaxError("Expected attribute value");
        }
        attrs[name] = value;
      }
      return attrs;
    }
    function parsePattern() {
      let first;
      if (test(RE_TEXT_RUN)) {
        first = match1(RE_TEXT_RUN);
      }
      if (source[cursor] === "{" || source[cursor] === "}") {
        return parsePatternElements(first ? [first] : [], Infinity);
      }
      let indent = parseIndent();
      if (indent) {
        if (first) {
          return parsePatternElements([first, indent], indent.length);
        }
        indent.value = trim(indent.value, RE_LEADING_NEWLINES);
        return parsePatternElements([indent], indent.length);
      }
      if (first) {
        return trim(first, RE_TRAILING_SPACES);
      }
      return null;
    }
    function parsePatternElements(elements = [], commonIndent) {
      while (true) {
        if (test(RE_TEXT_RUN)) {
          elements.push(match1(RE_TEXT_RUN));
          continue;
        }
        if (source[cursor] === "{") {
          elements.push(parsePlaceable());
          continue;
        }
        if (source[cursor] === "}") {
          throw new SyntaxError("Unbalanced closing brace");
        }
        let indent = parseIndent();
        if (indent) {
          elements.push(indent);
          commonIndent = Math.min(commonIndent, indent.length);
          continue;
        }
        break;
      }
      let lastIndex = elements.length - 1;
      let lastElement = elements[lastIndex];
      if (typeof lastElement === "string") {
        elements[lastIndex] = trim(lastElement, RE_TRAILING_SPACES);
      }
      let baked = [];
      for (let element of elements) {
        if (element instanceof Indent) {
          element = element.value.slice(0, element.value.length - commonIndent);
        }
        if (element) {
          baked.push(element);
        }
      }
      return baked;
    }
    function parsePlaceable() {
      consumeToken(TOKEN_BRACE_OPEN, SyntaxError);
      let selector = parseInlineExpression();
      if (consumeToken(TOKEN_BRACE_CLOSE)) {
        return selector;
      }
      if (consumeToken(TOKEN_ARROW)) {
        let variants = parseVariants();
        consumeToken(TOKEN_BRACE_CLOSE, SyntaxError);
        return {
          type: "select",
          selector,
          ...variants
        };
      }
      throw new SyntaxError("Unclosed placeable");
    }
    function parseInlineExpression() {
      if (source[cursor] === "{") {
        return parsePlaceable();
      }
      if (test(RE_REFERENCE)) {
        let [, sigil, name, attr = null] = match(RE_REFERENCE);
        if (sigil === "$") {
          return {
            type: "var",
            name
          };
        }
        if (consumeToken(TOKEN_PAREN_OPEN)) {
          let args = parseArguments();
          if (sigil === "-") {
            return {
              type: "term",
              name,
              attr,
              args
            };
          }
          if (RE_FUNCTION_NAME.test(name)) {
            return {
              type: "func",
              name,
              args
            };
          }
          throw new SyntaxError("Function names must be all upper-case");
        }
        if (sigil === "-") {
          return {
            type: "term",
            name,
            attr,
            args: []
          };
        }
        return {
          type: "mesg",
          name,
          attr
        };
      }
      return parseLiteral();
    }
    function parseArguments() {
      let args = [];
      while (true) {
        switch (source[cursor]) {
          case ")":
            cursor++;
            return args;
          case undefined:
            throw new SyntaxError("Unclosed argument list");
        }
        args.push(parseArgument());
        consumeToken(TOKEN_COMMA);
      }
    }
    function parseArgument() {
      let expr = parseInlineExpression();
      if (expr.type !== "mesg") {
        return expr;
      }
      if (consumeToken(TOKEN_COLON)) {
        return {
          type: "narg",
          name: expr.name,
          value: parseLiteral()
        };
      }
      return expr;
    }
    function parseVariants() {
      let variants = [];
      let count = 0;
      let star;
      while (test(RE_VARIANT_START)) {
        if (consumeChar("*")) {
          star = count;
        }
        let key = parseVariantKey();
        let value = parsePattern();
        if (value === null) {
          throw new SyntaxError("Expected variant value");
        }
        variants[count++] = {
          key,
          value
        };
      }
      if (count === 0) {
        return null;
      }
      if (star === undefined) {
        throw new SyntaxError("Expected default variant");
      }
      return {
        variants,
        star
      };
    }
    function parseVariantKey() {
      consumeToken(TOKEN_BRACKET_OPEN, SyntaxError);
      let key;
      if (test(RE_NUMBER_LITERAL)) {
        key = parseNumberLiteral();
      } else {
        key = {
          type: "str",
          value: match1(RE_IDENTIFIER)
        };
      }
      consumeToken(TOKEN_BRACKET_CLOSE, SyntaxError);
      return key;
    }
    function parseLiteral() {
      if (test(RE_NUMBER_LITERAL)) {
        return parseNumberLiteral();
      }
      if (source[cursor] === '"') {
        return parseStringLiteral();
      }
      throw new SyntaxError("Invalid expression");
    }
    function parseNumberLiteral() {
      let [, value, fraction = ""] = match(RE_NUMBER_LITERAL);
      let precision = fraction.length;
      return {
        type: "num",
        value: parseFloat(value),
        precision
      };
    }
    function parseStringLiteral() {
      consumeChar('"', SyntaxError);
      let value = "";
      while (true) {
        value += match1(RE_STRING_RUN);
        if (source[cursor] === "\\") {
          value += parseEscapeSequence();
          continue;
        }
        if (consumeChar('"')) {
          return {
            type: "str",
            value
          };
        }
        throw new SyntaxError("Unclosed string literal");
      }
    }
    function parseEscapeSequence() {
      if (test(RE_STRING_ESCAPE)) {
        return match1(RE_STRING_ESCAPE);
      }
      if (test(RE_UNICODE_ESCAPE)) {
        let [, codepoint4, codepoint6] = match(RE_UNICODE_ESCAPE);
        let codepoint = parseInt(codepoint4 || codepoint6, 16);
        return codepoint <= 0xd7ff || 0xe000 <= codepoint ? String.fromCodePoint(codepoint) : "�";
      }
      throw new SyntaxError("Unknown escape sequence");
    }
    function parseIndent() {
      let start = cursor;
      consumeToken(TOKEN_BLANK);
      switch (source[cursor]) {
        case ".":
        case "[":
        case "*":
        case "}":
        case undefined:
          return false;
        case "{":
          return makeIndent(source.slice(start, cursor));
      }
      if (source[cursor - 1] === " ") {
        return makeIndent(source.slice(start, cursor));
      }
      return false;
    }
    function trim(text, re) {
      return text.replace(re, "");
    }
    function makeIndent(blank) {
      let value = blank.replace(RE_BLANK_LINES, "\n");
      let length = RE_INDENT.exec(blank)[1].length;
      return new Indent(value, length);
    }
  }
}
class Indent {
  constructor(value, length) {
    this.value = value;
    this.length = length;
  }
}
;// ./node_modules/@fluent/bundle/esm/index.js



;// ./node_modules/@fluent/dom/esm/overlay.js
const reOverlay = /<|&#?\w+;/;
const TEXT_LEVEL_ELEMENTS = {
  "http://www.w3.org/1999/xhtml": ["em", "strong", "small", "s", "cite", "q", "dfn", "abbr", "data", "time", "code", "var", "samp", "kbd", "sub", "sup", "i", "b", "u", "mark", "bdi", "bdo", "span", "br", "wbr"]
};
const LOCALIZABLE_ATTRIBUTES = {
  "http://www.w3.org/1999/xhtml": {
    global: ["title", "aria-description", "aria-label", "aria-valuetext"],
    a: ["download"],
    area: ["download", "alt"],
    input: ["alt", "placeholder"],
    menuitem: ["label"],
    menu: ["label"],
    optgroup: ["label"],
    option: ["label"],
    track: ["label"],
    img: ["alt"],
    textarea: ["placeholder"],
    th: ["abbr"]
  },
  "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul": {
    global: ["accesskey", "aria-label", "aria-valuetext", "label", "title", "tooltiptext"],
    description: ["value"],
    key: ["key", "keycode"],
    label: ["value"],
    textbox: ["placeholder", "value"]
  }
};
function translateElement(element, translation) {
  const {
    value
  } = translation;
  if (typeof value === "string") {
    if (element.localName === "title" && element.namespaceURI === "http://www.w3.org/1999/xhtml") {
      element.textContent = value;
    } else if (!reOverlay.test(value)) {
      element.textContent = value;
    } else {
      const templateElement = element.ownerDocument.createElementNS("http://www.w3.org/1999/xhtml", "template");
      templateElement.innerHTML = value;
      overlayChildNodes(templateElement.content, element);
    }
  }
  overlayAttributes(translation, element);
}
function overlayChildNodes(fromFragment, toElement) {
  for (const childNode of fromFragment.childNodes) {
    if (childNode.nodeType === childNode.TEXT_NODE) {
      continue;
    }
    if (childNode.hasAttribute("data-l10n-name")) {
      const sanitized = getNodeForNamedElement(toElement, childNode);
      fromFragment.replaceChild(sanitized, childNode);
      continue;
    }
    if (isElementAllowed(childNode)) {
      const sanitized = createSanitizedElement(childNode);
      fromFragment.replaceChild(sanitized, childNode);
      continue;
    }
    console.warn(`An element of forbidden type "${childNode.localName}" was found in ` + "the translation. Only safe text-level elements and elements with " + "data-l10n-name are allowed.");
    fromFragment.replaceChild(createTextNodeFromTextContent(childNode), childNode);
  }
  toElement.textContent = "";
  toElement.appendChild(fromFragment);
}
function hasAttribute(attributes, name) {
  if (!attributes) {
    return false;
  }
  for (let attr of attributes) {
    if (attr.name === name) {
      return true;
    }
  }
  return false;
}
function overlayAttributes(fromElement, toElement) {
  const explicitlyAllowed = toElement.hasAttribute("data-l10n-attrs") ? toElement.getAttribute("data-l10n-attrs").split(",").map(i => i.trim()) : null;
  for (const attr of Array.from(toElement.attributes)) {
    if (isAttrNameLocalizable(attr.name, toElement, explicitlyAllowed) && !hasAttribute(fromElement.attributes, attr.name)) {
      toElement.removeAttribute(attr.name);
    }
  }
  if (!fromElement.attributes) {
    return;
  }
  for (const attr of Array.from(fromElement.attributes)) {
    if (isAttrNameLocalizable(attr.name, toElement, explicitlyAllowed) && toElement.getAttribute(attr.name) !== attr.value) {
      toElement.setAttribute(attr.name, attr.value);
    }
  }
}
function getNodeForNamedElement(sourceElement, translatedChild) {
  const childName = translatedChild.getAttribute("data-l10n-name");
  const sourceChild = sourceElement.querySelector(`[data-l10n-name="${childName}"]`);
  if (!sourceChild) {
    console.warn(`An element named "${childName}" wasn't found in the source.`);
    return createTextNodeFromTextContent(translatedChild);
  }
  if (sourceChild.localName !== translatedChild.localName) {
    console.warn(`An element named "${childName}" was found in the translation ` + `but its type ${translatedChild.localName} didn't match the ` + `element found in the source (${sourceChild.localName}).`);
    return createTextNodeFromTextContent(translatedChild);
  }
  sourceElement.removeChild(sourceChild);
  const clone = sourceChild.cloneNode(false);
  return shallowPopulateUsing(translatedChild, clone);
}
function createSanitizedElement(element) {
  const clone = element.ownerDocument.createElement(element.localName);
  return shallowPopulateUsing(element, clone);
}
function createTextNodeFromTextContent(element) {
  return element.ownerDocument.createTextNode(element.textContent);
}
function isElementAllowed(element) {
  const allowed = TEXT_LEVEL_ELEMENTS[element.namespaceURI];
  return allowed && allowed.includes(element.localName);
}
function isAttrNameLocalizable(name, element, explicitlyAllowed = null) {
  if (explicitlyAllowed && explicitlyAllowed.includes(name)) {
    return true;
  }
  const allowed = LOCALIZABLE_ATTRIBUTES[element.namespaceURI];
  if (!allowed) {
    return false;
  }
  const attrName = name.toLowerCase();
  const elemName = element.localName;
  if (allowed.global.includes(attrName)) {
    return true;
  }
  if (!allowed[elemName]) {
    return false;
  }
  if (allowed[elemName].includes(attrName)) {
    return true;
  }
  if (element.namespaceURI === "http://www.w3.org/1999/xhtml" && elemName === "input" && attrName === "value") {
    const type = element.type.toLowerCase();
    if (type === "submit" || type === "button" || type === "reset") {
      return true;
    }
  }
  return false;
}
function shallowPopulateUsing(fromElement, toElement) {
  toElement.textContent = fromElement.textContent;
  overlayAttributes(fromElement, toElement);
  return toElement;
}
;// ./node_modules/cached-iterable/src/cached_iterable.mjs
class CachedIterable extends Array {
  static from(iterable) {
    if (iterable instanceof this) {
      return iterable;
    }
    return new this(iterable);
  }
}
;// ./node_modules/cached-iterable/src/cached_sync_iterable.mjs

class CachedSyncIterable extends CachedIterable {
  constructor(iterable) {
    super();
    if (Symbol.iterator in Object(iterable)) {
      this.iterator = iterable[Symbol.iterator]();
    } else {
      throw new TypeError("Argument must implement the iteration protocol.");
    }
  }
  [Symbol.iterator]() {
    const cached = this;
    let cur = 0;
    return {
      next() {
        if (cached.length <= cur) {
          cached.push(cached.iterator.next());
        }
        return cached[cur++];
      }
    };
  }
  touchNext(count = 1) {
    let idx = 0;
    while (idx++ < count) {
      const last = this[this.length - 1];
      if (last && last.done) {
        break;
      }
      this.push(this.iterator.next());
    }
    return this[this.length - 1];
  }
}
;// ./node_modules/cached-iterable/src/cached_async_iterable.mjs

class CachedAsyncIterable extends CachedIterable {
  constructor(iterable) {
    super();
    if (Symbol.asyncIterator in Object(iterable)) {
      this.iterator = iterable[Symbol.asyncIterator]();
    } else if (Symbol.iterator in Object(iterable)) {
      this.iterator = iterable[Symbol.iterator]();
    } else {
      throw new TypeError("Argument must implement the iteration protocol.");
    }
  }
  [Symbol.asyncIterator]() {
    const cached = this;
    let cur = 0;
    return {
      async next() {
        if (cached.length <= cur) {
          cached.push(cached.iterator.next());
        }
        return cached[cur++];
      }
    };
  }
  async touchNext(count = 1) {
    let idx = 0;
    while (idx++ < count) {
      const last = this[this.length - 1];
      if (last && (await last).done) {
        break;
      }
      this.push(this.iterator.next());
    }
    return this[this.length - 1];
  }
}
;// ./node_modules/cached-iterable/src/index.mjs


;// ./node_modules/@fluent/dom/esm/localization.js

class Localization {
  constructor(resourceIds = [], generateBundles) {
    this.resourceIds = resourceIds;
    this.generateBundles = generateBundles;
    this.onChange(true);
  }
  addResourceIds(resourceIds, eager = false) {
    this.resourceIds.push(...resourceIds);
    this.onChange(eager);
    return this.resourceIds.length;
  }
  removeResourceIds(resourceIds) {
    this.resourceIds = this.resourceIds.filter(r => !resourceIds.includes(r));
    this.onChange();
    return this.resourceIds.length;
  }
  async formatWithFallback(keys, method) {
    const translations = [];
    let hasAtLeastOneBundle = false;
    for await (const bundle of this.bundles) {
      hasAtLeastOneBundle = true;
      const missingIds = keysFromBundle(method, bundle, keys, translations);
      if (missingIds.size === 0) {
        break;
      }
      if (typeof console !== "undefined") {
        const locale = bundle.locales[0];
        const ids = Array.from(missingIds).join(", ");
        console.warn(`[fluent] Missing translations in ${locale}: ${ids}`);
      }
    }
    if (!hasAtLeastOneBundle && typeof console !== "undefined") {
      console.warn(`[fluent] Request for keys failed because no resource bundles got generated.
  keys: ${JSON.stringify(keys)}.
  resourceIds: ${JSON.stringify(this.resourceIds)}.`);
    }
    return translations;
  }
  formatMessages(keys) {
    return this.formatWithFallback(keys, messageFromBundle);
  }
  formatValues(keys) {
    return this.formatWithFallback(keys, valueFromBundle);
  }
  async formatValue(id, args) {
    const [val] = await this.formatValues([{
      id,
      args
    }]);
    return val;
  }
  handleEvent() {
    this.onChange();
  }
  onChange(eager = false) {
    this.bundles = CachedAsyncIterable.from(this.generateBundles(this.resourceIds));
    if (eager) {
      this.bundles.touchNext(2);
    }
  }
}
function valueFromBundle(bundle, errors, message, args) {
  if (message.value) {
    return bundle.formatPattern(message.value, args, errors);
  }
  return null;
}
function messageFromBundle(bundle, errors, message, args) {
  const formatted = {
    value: null,
    attributes: null
  };
  if (message.value) {
    formatted.value = bundle.formatPattern(message.value, args, errors);
  }
  let attrNames = Object.keys(message.attributes);
  if (attrNames.length > 0) {
    formatted.attributes = new Array(attrNames.length);
    for (let [i, name] of attrNames.entries()) {
      let value = bundle.formatPattern(message.attributes[name], args, errors);
      formatted.attributes[i] = {
        name,
        value
      };
    }
  }
  return formatted;
}
function keysFromBundle(method, bundle, keys, translations) {
  const messageErrors = [];
  const missingIds = new Set();
  keys.forEach(({
    id,
    args
  }, i) => {
    if (translations[i] !== undefined) {
      return;
    }
    let message = bundle.getMessage(id);
    if (message) {
      messageErrors.length = 0;
      translations[i] = method(bundle, messageErrors, message, args);
      if (messageErrors.length > 0 && typeof console !== "undefined") {
        const locale = bundle.locales[0];
        const errors = messageErrors.join(", ");
        console.warn(`[fluent][resolver] errors in ${locale}/${id}: ${errors}.`);
      }
    } else {
      missingIds.add(id);
    }
  });
  return missingIds;
}
;// ./node_modules/@fluent/dom/esm/dom_localization.js


const L10NID_ATTR_NAME = "data-l10n-id";
const L10NARGS_ATTR_NAME = "data-l10n-args";
const L10N_ELEMENT_QUERY = `[${L10NID_ATTR_NAME}]`;
class DOMLocalization extends Localization {
  constructor(resourceIds, generateBundles) {
    super(resourceIds, generateBundles);
    this.roots = new Set();
    this.pendingrAF = null;
    this.pendingElements = new Set();
    this.windowElement = null;
    this.mutationObserver = null;
    this.observerConfig = {
      attributes: true,
      characterData: false,
      childList: true,
      subtree: true,
      attributeFilter: [L10NID_ATTR_NAME, L10NARGS_ATTR_NAME]
    };
  }
  onChange(eager = false) {
    super.onChange(eager);
    if (this.roots) {
      this.translateRoots();
    }
  }
  setAttributes(element, id, args) {
    element.setAttribute(L10NID_ATTR_NAME, id);
    if (args) {
      element.setAttribute(L10NARGS_ATTR_NAME, JSON.stringify(args));
    } else {
      element.removeAttribute(L10NARGS_ATTR_NAME);
    }
    return element;
  }
  getAttributes(element) {
    return {
      id: element.getAttribute(L10NID_ATTR_NAME),
      args: JSON.parse(element.getAttribute(L10NARGS_ATTR_NAME) || null)
    };
  }
  connectRoot(newRoot) {
    for (const root of this.roots) {
      if (root === newRoot || root.contains(newRoot) || newRoot.contains(root)) {
        throw new Error("Cannot add a root that overlaps with existing root.");
      }
    }
    if (this.windowElement) {
      if (this.windowElement !== newRoot.ownerDocument.defaultView) {
        throw new Error(`Cannot connect a root:
          DOMLocalization already has a root from a different window.`);
      }
    } else {
      this.windowElement = newRoot.ownerDocument.defaultView;
      this.mutationObserver = new this.windowElement.MutationObserver(mutations => this.translateMutations(mutations));
    }
    this.roots.add(newRoot);
    this.mutationObserver.observe(newRoot, this.observerConfig);
  }
  disconnectRoot(root) {
    this.roots.delete(root);
    this.pauseObserving();
    if (this.roots.size === 0) {
      this.mutationObserver = null;
      if (this.windowElement && this.pendingrAF) {
        this.windowElement.cancelAnimationFrame(this.pendingrAF);
      }
      this.windowElement = null;
      this.pendingrAF = null;
      this.pendingElements.clear();
      return true;
    }
    this.resumeObserving();
    return false;
  }
  translateRoots() {
    const roots = Array.from(this.roots);
    return Promise.all(roots.map(root => this.translateFragment(root)));
  }
  pauseObserving() {
    if (!this.mutationObserver) {
      return;
    }
    this.translateMutations(this.mutationObserver.takeRecords());
    this.mutationObserver.disconnect();
  }
  resumeObserving() {
    if (!this.mutationObserver) {
      return;
    }
    for (const root of this.roots) {
      this.mutationObserver.observe(root, this.observerConfig);
    }
  }
  translateMutations(mutations) {
    for (const mutation of mutations) {
      switch (mutation.type) {
        case "attributes":
          if (mutation.target.hasAttribute("data-l10n-id")) {
            this.pendingElements.add(mutation.target);
          }
          break;
        case "childList":
          for (const addedNode of mutation.addedNodes) {
            if (addedNode.nodeType === addedNode.ELEMENT_NODE) {
              if (addedNode.childElementCount) {
                for (const element of this.getTranslatables(addedNode)) {
                  this.pendingElements.add(element);
                }
              } else if (addedNode.hasAttribute(L10NID_ATTR_NAME)) {
                this.pendingElements.add(addedNode);
              }
            }
          }
          break;
      }
    }
    if (this.pendingElements.size > 0) {
      if (this.pendingrAF === null) {
        this.pendingrAF = this.windowElement.requestAnimationFrame(() => {
          this.translateElements(Array.from(this.pendingElements));
          this.pendingElements.clear();
          this.pendingrAF = null;
        });
      }
    }
  }
  translateFragment(frag) {
    return this.translateElements(this.getTranslatables(frag));
  }
  async translateElements(elements) {
    if (!elements.length) {
      return undefined;
    }
    const keys = elements.map(this.getKeysForElement);
    const translations = await this.formatMessages(keys);
    return this.applyTranslations(elements, translations);
  }
  applyTranslations(elements, translations) {
    this.pauseObserving();
    for (let i = 0; i < elements.length; i++) {
      if (translations[i] !== undefined) {
        translateElement(elements[i], translations[i]);
      }
    }
    this.resumeObserving();
  }
  getTranslatables(element) {
    const nodes = Array.from(element.querySelectorAll(L10N_ELEMENT_QUERY));
    if (typeof element.hasAttribute === "function" && element.hasAttribute(L10NID_ATTR_NAME)) {
      nodes.push(element);
    }
    return nodes;
  }
  getKeysForElement(element) {
    return {
      id: element.getAttribute(L10NID_ATTR_NAME),
      args: JSON.parse(element.getAttribute(L10NARGS_ATTR_NAME) || null)
    };
  }
}
;// ./node_modules/@fluent/dom/esm/index.js


;// ./web/l10n.js
class L10n {
  #dir;
  #elements;
  #lang;
  #l10n;
  constructor({
    lang,
    isRTL
  }, l10n = null) {
    this.#lang = L10n.#fixupLangCode(lang);
    this.#l10n = l10n;
    this.#dir = isRTL ?? L10n.#isRTL(this.#lang) ? "rtl" : "ltr";
  }
  _setL10n(l10n) {
    this.#l10n = l10n;
  }
  getLanguage() {
    return this.#lang;
  }
  getDirection() {
    return this.#dir;
  }
  async get(ids, args = null) {
    if (Array.isArray(ids)) {
      ids = ids.map(id => ({
        id
      }));
      const messages = await this.#l10n.formatMessages(ids);
      return messages.map(message => message.value);
    }
    const messages = await this.#l10n.formatMessages([{
      id: ids,
      args
    }]);
    return messages[0]?.value;
  }
  async translate(element) {
    (this.#elements ||= new Set()).add(element);
    try {
      this.#l10n.connectRoot(element);
      await this.#l10n.translateRoots();
    } catch {}
  }
  async translateOnce(element) {
    try {
      await this.#l10n.translateElements([element]);
    } catch (ex) {
      console.error("translateOnce:", ex);
    }
  }
  async destroy() {
    if (this.#elements) {
      for (const element of this.#elements) {
        this.#l10n.disconnectRoot(element);
      }
      this.#elements.clear();
      this.#elements = null;
    }
    this.#l10n.pauseObserving();
  }
  pause() {
    this.#l10n.pauseObserving();
  }
  resume() {
    this.#l10n.resumeObserving();
  }
  static #fixupLangCode(langCode) {
    langCode = langCode?.toLowerCase() || "en-us";
    const PARTIAL_LANG_CODES = {
      en: "en-us",
      es: "es-es",
      fy: "fy-nl",
      ga: "ga-ie",
      gu: "gu-in",
      hi: "hi-in",
      hy: "hy-am",
      nb: "nb-no",
      ne: "ne-np",
      nn: "nn-no",
      pa: "pa-in",
      pt: "pt-pt",
      sv: "sv-se",
      zh: "zh-cn"
    };
    return PARTIAL_LANG_CODES[langCode] || langCode;
  }
  static #isRTL(lang) {
    const shortCode = lang.split("-", 1)[0];
    return ["ar", "he", "fa", "ps", "ur"].includes(shortCode);
  }
}
const GenericL10n = null;

;// ./web/genericl10n.js




function PLATFORM() {
  const {
    isAndroid,
    isLinux,
    isMac,
    isWindows
  } = FeatureTest.platform;
  if (isLinux) {
    return "linux";
  }
  if (isWindows) {
    return "windows";
  }
  if (isMac) {
    return "macos";
  }
  return isAndroid ? "android" : "other";
}
function createBundle(lang, text) {
  const resource = new FluentResource(text);
  const bundle = new FluentBundle(lang, {
    functions: {
      PLATFORM
    }
  });
  const errors = bundle.addResource(resource);
  if (errors.length) {
    console.error("L10n errors", errors);
  }
  return bundle;
}
class genericl10n_GenericL10n extends L10n {
  constructor(lang) {
    super({
      lang
    });
    const generateBundles = !lang ? genericl10n_GenericL10n.#generateBundlesFallback.bind(genericl10n_GenericL10n, this.getLanguage()) : genericl10n_GenericL10n.#generateBundles.bind(genericl10n_GenericL10n, "en-us", this.getLanguage());
    this._setL10n(new DOMLocalization([], generateBundles));
  }
  static async *#generateBundles(defaultLang, baseLang) {
    const {
      baseURL,
      paths
    } = await this.#getPaths();
    const langs = [baseLang];
    if (defaultLang !== baseLang) {
      const shortLang = baseLang.split("-", 1)[0];
      if (shortLang !== baseLang) {
        langs.push(shortLang);
      }
      langs.push(defaultLang);
    }
    const bundles = langs.map(lang => [lang, this.#createBundle(lang, baseURL, paths)]);
    for (const [lang, bundlePromise] of bundles) {
      const bundle = await bundlePromise;
      if (bundle) {
        yield bundle;
      } else if (lang === "en-us") {
        yield this.#createBundleFallback(lang);
      }
    }
  }
  static async #createBundle(lang, baseURL, paths) {
    const path = paths[lang];
    if (!path) {
      return null;
    }
    const url = new URL(path, baseURL);
    const text = await fetchData(url, "text");
    return createBundle(lang, text);
  }
  static async #getPaths() {
    try {
      const {
        href
      } = document.querySelector(`link[type="application/l10n"]`);
      const paths = await fetchData(href, "json");
      return {
        baseURL: href.substring(0, href.lastIndexOf("/") + 1) || "./",
        paths
      };
    } catch {}
    return {
      baseURL: "./",
      paths: Object.create(null)
    };
  }
  static async *#generateBundlesFallback(lang) {
    yield this.#createBundleFallback(lang);
  }
  static async #createBundleFallback(lang) {
    const text = "pdfjs-previous-button =\n    .title = Previous Page\npdfjs-previous-button-label = Previous\npdfjs-next-button =\n    .title = Next Page\npdfjs-next-button-label = Next\npdfjs-page-input =\n    .title = Page\npdfjs-of-pages = of { $pagesCount }\npdfjs-page-of-pages = ({ $pageNumber } of { $pagesCount })\npdfjs-zoom-out-button =\n    .title = Zoom Out\npdfjs-zoom-out-button-label = Zoom Out\npdfjs-zoom-in-button =\n    .title = Zoom In\npdfjs-zoom-in-button-label = Zoom In\npdfjs-zoom-select =\n    .title = Zoom\npdfjs-presentation-mode-button =\n    .title = Switch to Presentation Mode\npdfjs-presentation-mode-button-label = Presentation Mode\npdfjs-open-file-button =\n    .title = Open File\npdfjs-open-file-button-label = Open\npdfjs-print-button =\n    .title = Print\npdfjs-print-button-label = Print\npdfjs-save-button =\n    .title = Save\npdfjs-save-button-label = Save\npdfjs-download-button =\n    .title = Download\npdfjs-download-button-label = Download\npdfjs-bookmark-button =\n    .title = Current Page (View URL from Current Page)\npdfjs-bookmark-button-label = Current Page\npdfjs-tools-button =\n    .title = Tools\npdfjs-tools-button-label = Tools\npdfjs-first-page-button =\n    .title = Go to First Page\npdfjs-first-page-button-label = Go to First Page\npdfjs-last-page-button =\n    .title = Go to Last Page\npdfjs-last-page-button-label = Go to Last Page\npdfjs-page-rotate-cw-button =\n    .title = Rotate Clockwise\npdfjs-page-rotate-cw-button-label = Rotate Clockwise\npdfjs-page-rotate-ccw-button =\n    .title = Rotate Counterclockwise\npdfjs-page-rotate-ccw-button-label = Rotate Counterclockwise\npdfjs-cursor-text-select-tool-button =\n    .title = Enable Text Selection Tool\npdfjs-cursor-text-select-tool-button-label = Text Selection Tool\npdfjs-cursor-hand-tool-button =\n    .title = Enable Hand Tool\npdfjs-cursor-hand-tool-button-label = Hand Tool\npdfjs-scroll-page-button =\n    .title = Use Page Scrolling\npdfjs-scroll-page-button-label = Page Scrolling\npdfjs-scroll-vertical-button =\n    .title = Use Vertical Scrolling\npdfjs-scroll-vertical-button-label = Vertical Scrolling\npdfjs-scroll-horizontal-button =\n    .title = Use Horizontal Scrolling\npdfjs-scroll-horizontal-button-label = Horizontal Scrolling\npdfjs-scroll-wrapped-button =\n    .title = Use Wrapped Scrolling\npdfjs-scroll-wrapped-button-label = Wrapped Scrolling\npdfjs-spread-none-button =\n    .title = Do not join page spreads\npdfjs-spread-none-button-label = No Spreads\npdfjs-spread-odd-button =\n    .title = Join page spreads starting with odd-numbered pages\npdfjs-spread-odd-button-label = Odd Spreads\npdfjs-spread-even-button =\n    .title = Join page spreads starting with even-numbered pages\npdfjs-spread-even-button-label = Even Spreads\npdfjs-document-properties-button =\n    .title = Document Properties…\npdfjs-document-properties-button-label = Document Properties…\npdfjs-document-properties-file-name = File name:\npdfjs-document-properties-file-size = File size:\npdfjs-document-properties-size-kb = { NUMBER($kb, maximumSignificantDigits: 3) } KB ({ $b } bytes)\npdfjs-document-properties-size-mb = { NUMBER($mb, maximumSignificantDigits: 3) } MB ({ $b } bytes)\npdfjs-document-properties-title = Title:\npdfjs-document-properties-author = Author:\npdfjs-document-properties-subject = Subject:\npdfjs-document-properties-keywords = Keywords:\npdfjs-document-properties-creation-date = Creation Date:\npdfjs-document-properties-modification-date = Modification Date:\npdfjs-document-properties-date-time-string = { DATETIME($dateObj, dateStyle: \"short\", timeStyle: \"medium\") }\npdfjs-document-properties-creator = Creator:\npdfjs-document-properties-producer = PDF Producer:\npdfjs-document-properties-version = PDF Version:\npdfjs-document-properties-page-count = Page Count:\npdfjs-document-properties-page-size = Page Size:\npdfjs-document-properties-page-size-unit-inches = in\npdfjs-document-properties-page-size-unit-millimeters = mm\npdfjs-document-properties-page-size-orientation-portrait = portrait\npdfjs-document-properties-page-size-orientation-landscape = landscape\npdfjs-document-properties-page-size-name-a-three = A3\npdfjs-document-properties-page-size-name-a-four = A4\npdfjs-document-properties-page-size-name-letter = Letter\npdfjs-document-properties-page-size-name-legal = Legal\npdfjs-document-properties-page-size-dimension-string = { $width } × { $height } { $unit } ({ $orientation })\npdfjs-document-properties-page-size-dimension-name-string = { $width } × { $height } { $unit } ({ $name }, { $orientation })\npdfjs-document-properties-linearized = Fast Web View:\npdfjs-document-properties-linearized-yes = Yes\npdfjs-document-properties-linearized-no = No\npdfjs-document-properties-close-button = Close\npdfjs-print-progress-message = Preparing document for printing…\npdfjs-print-progress-percent = { $progress }%\npdfjs-print-progress-close-button = Cancel\npdfjs-printing-not-supported = Warning: Printing is not fully supported by this browser.\npdfjs-printing-not-ready = Warning: The PDF is not fully loaded for printing.\npdfjs-current-outline-item-button =\n    .title = Find Current Outline Item\npdfjs-current-outline-item-button-label = Current Outline Item\npdfjs-findbar-button =\n    .title = Find in Document\npdfjs-findbar-button-label = Find\npdfjs-additional-layers = Additional Layers\npdfjs-thumb-page-title1 =\n    .title = Page { $page } of { $total }\npdfjs-thumb-page-canvas =\n    .aria-label = Thumbnail of Page { $page }\npdfjs-thumb-page-checkbox1 =\n    .title = Select page { $page }\npdfjs-find-input =\n    .title = Find\n    .placeholder = Find in document…\npdfjs-find-previous-button =\n    .title = Find the previous occurrence of the phrase\npdfjs-find-previous-button-label = Previous\npdfjs-find-next-button =\n    .title = Find the next occurrence of the phrase\npdfjs-find-next-button-label = Next\npdfjs-find-highlight-checkbox = Highlight All\npdfjs-find-match-case-checkbox-label = Match Case\npdfjs-find-match-diacritics-checkbox-label = Match Diacritics\npdfjs-find-entire-word-checkbox-label = Whole Words\npdfjs-find-reached-top = Reached top of document, continued from bottom\npdfjs-find-reached-bottom = Reached end of document, continued from top\npdfjs-find-match-count =\n    { $total ->\n        [one] { $current } of { $total } match\n       *[other] { $current } of { $total } matches\n    }\npdfjs-find-match-count-limit =\n    { $limit ->\n        [one] More than { $limit } match\n       *[other] More than { $limit } matches\n    }\npdfjs-find-not-found = Phrase not found\npdfjs-page-scale-width = Page Width\npdfjs-page-scale-fit = Page Fit\npdfjs-page-scale-auto = Automatic Zoom\npdfjs-page-scale-actual = Actual Size\npdfjs-page-scale-percent = { $scale }%\npdfjs-page-landmark =\n    .aria-label = Page { $page }\npdfjs-loading-error = An error occurred while loading the PDF.\npdfjs-invalid-file-error = Invalid or corrupted PDF file.\npdfjs-missing-file-error = Missing PDF file.\npdfjs-unexpected-response-error = Unexpected server response.\npdfjs-rendering-error = An error occurred while rendering the page.\npdfjs-annotation-date-time-string = { DATETIME($dateObj, dateStyle: \"short\", timeStyle: \"medium\") }\npdfjs-text-annotation-type =\n    .alt = [{ $type } Annotation]\npdfjs-password-label = Enter the password to open this PDF file.\npdfjs-password-invalid = Invalid password. Please try again.\npdfjs-password-ok-button = OK\npdfjs-password-cancel-button = Cancel\npdfjs-web-fonts-disabled = Web fonts are disabled: unable to use embedded PDF fonts.\npdfjs-editor-free-text-button =\n    .title = Text\npdfjs-editor-color-picker-free-text-input =\n    .title = Change text color\npdfjs-editor-free-text-button-label = Text\npdfjs-editor-ink-button =\n    .title = Draw\npdfjs-editor-color-picker-ink-input =\n    .title = Change drawing color\npdfjs-editor-ink-button-label = Draw\npdfjs-editor-stamp-button =\n    .title = Add or edit images\npdfjs-editor-stamp-button-label = Add or edit images\npdfjs-editor-highlight-button =\n    .title = Highlight\npdfjs-editor-highlight-button-label = Highlight\npdfjs-highlight-floating-button1 =\n    .title = Highlight\n    .aria-label = Highlight\npdfjs-highlight-floating-button-label = Highlight\npdfjs-comment-floating-button =\n    .title = Comment\n    .aria-label = Comment\npdfjs-comment-floating-button-label = Comment\npdfjs-editor-comment-button =\n    .title = Comment\n    .aria-label = Comment\npdfjs-editor-comment-button-label = Comment\npdfjs-editor-signature-button =\n    .title = Add signature\npdfjs-editor-signature-button-label = Add signature\npdfjs-editor-highlight-editor =\n    .aria-label = Highlight editor\npdfjs-editor-ink-editor =\n    .aria-label = Drawing editor\npdfjs-editor-signature-editor1 =\n    .aria-description = Signature editor: { $description }\npdfjs-editor-stamp-editor =\n    .aria-label = Image editor\npdfjs-editor-remove-ink-button =\n    .title = Remove drawing\npdfjs-editor-remove-freetext-button =\n    .title = Remove text\npdfjs-editor-remove-stamp-button =\n    .title = Remove image\npdfjs-editor-remove-highlight-button =\n    .title = Remove highlight\npdfjs-editor-remove-signature-button =\n    .title = Remove signature\npdfjs-editor-free-text-color-input = Color\npdfjs-editor-free-text-size-input = Size\npdfjs-editor-ink-color-input = Color\npdfjs-editor-ink-thickness-input = Thickness\npdfjs-editor-ink-opacity-input = Opacity\npdfjs-editor-stamp-add-image-button =\n    .title = Add image\npdfjs-editor-stamp-add-image-button-label = Add image\npdfjs-editor-free-highlight-thickness-input = Thickness\npdfjs-editor-free-highlight-thickness-title =\n    .title = Change thickness when highlighting items other than text\npdfjs-editor-add-signature-container =\n    .aria-label = Signature controls and saved signatures\npdfjs-editor-signature-add-signature-button =\n    .title = Add new signature\npdfjs-editor-signature-add-signature-button-label = Add new signature\npdfjs-editor-add-saved-signature-button =\n    .title = Saved signature: { $description }\npdfjs-free-text2 =\n    .aria-label = Text Editor\n    .default-content = Start typing…\npdfjs-editor-comments-sidebar-title =\n    { $count ->\n        [one] Comment\n       *[other] Comments\n    }\npdfjs-editor-comments-sidebar-close-button =\n    .title = Close the sidebar\n    .aria-label = Close the sidebar\npdfjs-editor-comments-sidebar-close-button-label = Close the sidebar\npdfjs-editor-comments-sidebar-no-comments1 = See something noteworthy? Highlight it and leave a comment.\npdfjs-editor-comments-sidebar-no-comments-link = Learn more\npdfjs-editor-alt-text-button =\n    .aria-label = Alt text\npdfjs-editor-alt-text-button-label = Alt text\npdfjs-editor-alt-text-edit-button =\n    .aria-label = Edit alt text\npdfjs-editor-alt-text-dialog-label = Choose an option\npdfjs-editor-alt-text-dialog-description = Alt text (alternative text) helps when people can’t see the image or when it doesn’t load.\npdfjs-editor-alt-text-add-description-label = Add a description\npdfjs-editor-alt-text-add-description-description = Aim for 1-2 sentences that describe the subject, setting, or actions.\npdfjs-editor-alt-text-mark-decorative-label = Mark as decorative\npdfjs-editor-alt-text-mark-decorative-description = This is used for ornamental images, like borders or watermarks.\npdfjs-editor-alt-text-cancel-button = Cancel\npdfjs-editor-alt-text-save-button = Save\npdfjs-editor-alt-text-decorative-tooltip = Marked as decorative\npdfjs-editor-alt-text-textarea =\n    .placeholder = For example, “A young man sits down at a table to eat a meal”\npdfjs-editor-resizer-top-left =\n    .aria-label = Top left corner — resize\npdfjs-editor-resizer-top-middle =\n    .aria-label = Top middle — resize\npdfjs-editor-resizer-top-right =\n    .aria-label = Top right corner — resize\npdfjs-editor-resizer-middle-right =\n    .aria-label = Middle right — resize\npdfjs-editor-resizer-bottom-right =\n    .aria-label = Bottom right corner — resize\npdfjs-editor-resizer-bottom-middle =\n    .aria-label = Bottom middle — resize\npdfjs-editor-resizer-bottom-left =\n    .aria-label = Bottom left corner — resize\npdfjs-editor-resizer-middle-left =\n    .aria-label = Middle left — resize\npdfjs-editor-highlight-colorpicker-label = Highlight color\npdfjs-editor-colorpicker-button =\n    .title = Change color\npdfjs-editor-colorpicker-dropdown =\n    .aria-label = Color choices\npdfjs-editor-colorpicker-yellow =\n    .title = Yellow\npdfjs-editor-colorpicker-green =\n    .title = Green\npdfjs-editor-colorpicker-blue =\n    .title = Blue\npdfjs-editor-colorpicker-pink =\n    .title = Pink\npdfjs-editor-colorpicker-red =\n    .title = Red\npdfjs-editor-highlight-show-all-button-label = Show all\npdfjs-editor-highlight-show-all-button =\n    .title = Show all\npdfjs-editor-new-alt-text-dialog-edit-label = Edit alt text (image description)\npdfjs-editor-new-alt-text-dialog-add-label = Add alt text (image description)\npdfjs-editor-new-alt-text-textarea =\n    .placeholder = Write your description here…\npdfjs-editor-new-alt-text-description = Short description for people who can’t see the image or when the image doesn’t load.\npdfjs-editor-new-alt-text-disclaimer1 = This alt text was created automatically and may be inaccurate.\npdfjs-editor-new-alt-text-disclaimer-learn-more-url = Learn more\npdfjs-editor-new-alt-text-create-automatically-button-label = Create alt text automatically\npdfjs-editor-new-alt-text-not-now-button = Not now\npdfjs-editor-new-alt-text-error-title = Couldn’t create alt text automatically\npdfjs-editor-new-alt-text-error-description = Please write your own alt text or try again later.\npdfjs-editor-new-alt-text-error-close-button = Close\npdfjs-editor-new-alt-text-ai-model-downloading-progress = Downloading alt text AI model ({ $downloadedSize } of { $totalSize } MB)\n    .aria-valuetext = Downloading alt text AI model ({ $downloadedSize } of { $totalSize } MB)\npdfjs-editor-new-alt-text-added-button =\n    .aria-label = Alt text added\npdfjs-editor-new-alt-text-added-button-label = Alt text added\npdfjs-editor-new-alt-text-missing-button =\n    .aria-label = Missing alt text\npdfjs-editor-new-alt-text-missing-button-label = Missing alt text\npdfjs-editor-new-alt-text-to-review-button =\n    .aria-label = Review alt text\npdfjs-editor-new-alt-text-to-review-button-label = Review alt text\npdfjs-editor-new-alt-text-generated-alt-text-with-disclaimer = Created automatically: { $generatedAltText }\npdfjs-image-alt-text-settings-button =\n    .title = Image alt text settings\npdfjs-image-alt-text-settings-button-label = Image alt text settings\npdfjs-editor-alt-text-settings-dialog-label = Image alt text settings\npdfjs-editor-alt-text-settings-automatic-title = Automatic alt text\npdfjs-editor-alt-text-settings-create-model-button-label = Create alt text automatically\npdfjs-editor-alt-text-settings-create-model-description = Suggests descriptions to help people who can’t see the image or when the image doesn’t load.\npdfjs-editor-alt-text-settings-editor-title = Alt text editor\npdfjs-editor-alt-text-settings-show-dialog-button-label = Show alt text editor right away when adding an image\npdfjs-editor-alt-text-settings-show-dialog-description = Helps you make sure all your images have alt text.\npdfjs-editor-alt-text-settings-close-button = Close\npdfjs-editor-highlight-added-alert = Highlight added\npdfjs-editor-freetext-added-alert = Text added\npdfjs-editor-ink-added-alert = Drawing added\npdfjs-editor-stamp-added-alert = Image added\npdfjs-editor-signature-added-alert = Signature added\npdfjs-editor-undo-bar-message-highlight = Highlight removed\npdfjs-editor-undo-bar-message-freetext = Text removed\npdfjs-editor-undo-bar-message-ink = Drawing removed\npdfjs-editor-undo-bar-message-stamp = Image removed\npdfjs-editor-undo-bar-message-signature = Signature removed\npdfjs-editor-undo-bar-message-comment = Comment removed\npdfjs-editor-undo-bar-message-multiple =\n    { $count ->\n        [one] { $count } annotation removed\n       *[other] { $count } annotations removed\n    }\npdfjs-editor-undo-bar-undo-button =\n    .title = Undo\npdfjs-editor-undo-bar-undo-button-label = Undo\npdfjs-editor-undo-bar-close-button =\n    .title = Close\npdfjs-editor-undo-bar-close-button-label = Close\npdfjs-editor-add-signature-dialog-label = This modal allows the user to create a signature to add to a PDF document. The user can edit the name (which also serves as the alt text), and optionally save the signature for repeated use.\npdfjs-editor-add-signature-dialog-title = Add a signature\npdfjs-editor-add-signature-type-button = Type\n    .title = Type\npdfjs-editor-add-signature-draw-button = Draw\n    .title = Draw\npdfjs-editor-add-signature-image-button = Image\n    .title = Image\npdfjs-editor-add-signature-type-input =\n    .aria-label = Type your signature\n    .placeholder = Type your signature\npdfjs-editor-add-signature-draw-placeholder = Draw your signature\npdfjs-editor-add-signature-draw-thickness-range-label = Thickness\npdfjs-editor-add-signature-draw-thickness-range =\n    .title = Drawing thickness: { $thickness }\npdfjs-editor-add-signature-image-placeholder = Drag a file here to upload\npdfjs-editor-add-signature-image-browse-link =\n    { PLATFORM() ->\n        [macos] Or choose image files\n       *[other] Or browse image files\n    }\npdfjs-editor-add-signature-description-label = Description (alt text)\npdfjs-editor-add-signature-description-input =\n    .title = Description (alt text)\npdfjs-editor-add-signature-description-default-when-drawing = Signature\npdfjs-editor-add-signature-clear-button-label = Clear signature\npdfjs-editor-add-signature-clear-button =\n    .title = Clear signature\npdfjs-editor-add-signature-save-checkbox = Save signature\npdfjs-editor-add-signature-save-warning-message = You’ve reached the limit of 5 saved signatures. Remove one to save more.\npdfjs-editor-add-signature-image-upload-error-title = Couldn’t upload image\npdfjs-editor-add-signature-image-upload-error-description = Check your network connection or try another image.\npdfjs-editor-add-signature-image-no-data-error-title = Can’t convert this image into a signature\npdfjs-editor-add-signature-image-no-data-error-description = Please try uploading a different image.\npdfjs-editor-add-signature-error-close-button = Close\npdfjs-editor-add-signature-cancel-button = Cancel\npdfjs-editor-add-signature-add-button = Add\npdfjs-editor-delete-signature-button1 =\n    .title = Remove saved signature\npdfjs-editor-delete-signature-button-label1 = Remove saved signature\npdfjs-editor-add-signature-edit-button-label = Edit description\npdfjs-editor-edit-signature-dialog-title = Edit description\npdfjs-editor-edit-signature-update-button = Update\npdfjs-show-comment-button =\n    .title = Show comment\npdfjs-editor-edit-comment-popup-button-label = Edit comment\npdfjs-editor-edit-comment-popup-button =\n    .title = Edit comment\npdfjs-editor-delete-comment-popup-button-label = Remove comment\npdfjs-editor-delete-comment-popup-button =\n    .title = Remove comment\npdfjs-editor-edit-comment-dialog-title-when-editing = Edit comment\npdfjs-editor-edit-comment-dialog-save-button-when-editing = Update\npdfjs-editor-edit-comment-dialog-title-when-adding = Add comment\npdfjs-editor-edit-comment-dialog-save-button-when-adding = Add\npdfjs-editor-edit-comment-dialog-text-input =\n    .placeholder = Start typing…\npdfjs-editor-edit-comment-dialog-cancel-button = Cancel\npdfjs-editor-add-comment-button =\n    .title = Add comment\npdfjs-toggle-views-manager-button1 =\n    .title = Manage pages\npdfjs-toggle-views-manager-notification-button =\n    .title = Toggle Sidebar (document contains thumbnails/outline/attachments/layers)\npdfjs-toggle-views-manager-button1-label = Manage pages\npdfjs-views-manager-sidebar =\n    .aria-label = Sidebar\npdfjs-views-manager-sidebar-resizer =\n    .aria-label = Sidebar resizer\npdfjs-views-manager-view-selector-button =\n    .title = Views\npdfjs-views-manager-view-selector-button-label = Views\npdfjs-views-manager-pages-title = Pages\npdfjs-views-manager-outlines-title1 = Document outline\n    .title = Document outline (double-click to expand/collapse all items)\npdfjs-views-manager-attachments-title = Attachments\npdfjs-views-manager-layers-title1 = Layers\n    .title = Layers (double-click to reset all layers to the default state)\npdfjs-views-manager-pages-option-label = Pages\npdfjs-views-manager-outlines-option-label = Document outline\npdfjs-views-manager-attachments-option-label = Attachments\npdfjs-views-manager-layers-option-label = Layers\npdfjs-views-manager-add-file-button =\n    .title = Add file\npdfjs-views-manager-add-file-button-label = Add file\npdfjs-views-manager-pages-status-action-label =\n    { $count ->\n        [one] { $count } selected\n        *[other] { $count } selected\n    }\npdfjs-views-manager-pages-status-none-action-label = Select pages\npdfjs-views-manager-pages-status-action-button-label = Manage\npdfjs-views-manager-pages-status-copy-button-label = Copy\npdfjs-views-manager-pages-status-cut-button-label = Cut\npdfjs-views-manager-pages-status-delete-button-label = Delete\npdfjs-views-manager-pages-status-export-selected-button-label = Export selected…\npdfjs-views-manager-status-undo-cut-label =\n    { $count ->\n        [one] 1 page cut\n        *[other] { $count } pages cut\n    }\npdfjs-views-manager-pages-status-undo-copy-label =\n    { $count ->\n        [one] 1 page copied\n        *[other] { $count } pages copied\n    }\npdfjs-views-manager-pages-status-undo-delete-label =\n    { $count ->\n        [one] 1 page deleted\n        *[other] { $count } pages deleted\n    }\npdfjs-views-manager-status-undo-button-label = Undo\npdfjs-views-manager-status-done-button-label = Done\npdfjs-views-manager-status-close-button =\n    .title = Close\npdfjs-views-manager-status-close-button-label = Close\npdfjs-views-manager-paste-button-label = Paste\npdfjs-views-manager-paste-button-before =\n    .title = Paste before the first page\npdfjs-views-manager-paste-button-after =\n    .title = Paste after page { $page }\npdfjs-new-badge-content = NEW\npdfjs-views-manager-waiting-for-file = Uploading file…\npdfjs-digital-signature-properties-button =\n    .title = Digital signature properties\n    .aria-label = Digital signature properties\npdfjs-digital-signature-properties-button-label = Digital signature properties\npdfjs-digital-signature-properties-banner-verified = Document was signed with a valid digital signature\npdfjs-digital-signature-properties-banner-unknown =\n    { $count ->\n        [one] Document signed but { $count } digital signature could not be verified\n       *[other] Document signed but { $count } digital signatures could not be verified\n    }\npdfjs-digital-signature-properties-banner-untrusted =\n    { $count ->\n        [one] Document signed with { $count } certificate that is not trusted\n       *[other] Document signed with { $count } certificates that are not trusted\n    }\npdfjs-digital-signature-properties-banner-expired =\n    { $count ->\n        [one] Document signed with { $count } expired certificate\n       *[other] Document signed with { $count } expired certificates\n    }\npdfjs-digital-signature-properties-banner-invalid =\n    { $count ->\n        [one] Document has { $count } invalid digital signature\n       *[other] Document has { $count } invalid digital signatures\n    }\npdfjs-digital-signature-properties-banner-revoked =\n    { $count ->\n        [one] Document signed with { $count } revoked certificate\n       *[other] Document signed with { $count } revoked certificates\n    }\npdfjs-digital-signature-properties-status-verified = Status: Signature verified\npdfjs-digital-signature-properties-status-invalid = Status: Signature invalid\npdfjs-digital-signature-properties-status-unknown = Status: Unable to verify (unsupported)\npdfjs-digital-signature-properties-certificate-trusted = Certificate: Trusted ({ $issuer })\npdfjs-digital-signature-properties-certificate-unknown = Certificate: Unavailable\npdfjs-digital-signature-properties-certificate-untrusted = Certificate: Untrusted\npdfjs-digital-signature-properties-certificate-untrusted-unknown-issuer = Certificate: Unknown issuer ({ $issuer })\npdfjs-digital-signature-properties-certificate-untrusted-self-signed = Certificate: Self-signed ({ $issuer })\npdfjs-digital-signature-properties-certificate-untrusted-untrusted-issuer = Certificate: Untrusted issuer ({ $issuer })\npdfjs-digital-signature-properties-certificate-expired = Certificate: Expired\npdfjs-digital-signature-properties-certificate-expired-with-date = Certificate: Expired ({ DATETIME($dateObj, dateStyle: \"medium\") })\npdfjs-digital-signature-properties-certificate-revoked = Certificate: Revoked\npdfjs-digital-signature-properties-view-certificate = View certificate\npdfjs-digital-signature-properties-reason = Reason: { $reason }\npdfjs-digital-signature-properties-timestamp = Timestamp: { DATETIME($dateObj, dateStyle: \"short\", timeStyle: \"medium\") }\npdfjs-digital-signature-properties-sub-signatures =\n    { $count ->\n        [one] Sub-signature ({ $count })\n       *[other] Sub-signatures ({ $count })\n    }";
    return createBundle(lang, text);
  }
}

;// ./web/generic_scripting.js
/* unused harmony import specifier */ var generic_scripting_getPdfFilenameFromUrl;

async function docProperties(pdfDocument) {
  const url = "",
    baseUrl = "";
  const {
    info,
    metadata,
    contentDispositionFilename,
    contentLength
  } = await pdfDocument.getMetadata();
  return {
    ...info,
    baseURL: baseUrl,
    filesize: contentLength || (await pdfDocument.getDownloadInfo()).length,
    filename: contentDispositionFilename || generic_scripting_getPdfFilenameFromUrl(url),
    metadata: metadata?.getRaw(),
    authors: metadata?.get("dc:creator"),
    numPages: pdfDocument.numPages,
    URL: url
  };
}
class GenericScripting {
  constructor(sandboxBundleSrc, wasmUrl) {
    this._ready = new Promise((resolve, reject) => {
      const sandbox = import(
      /*webpackIgnore: true*/
      /*@vite-ignore*/
      sandboxBundleSrc);
      sandbox.then(pdfjsSandbox => {
        resolve(pdfjsSandbox.QuickJSSandbox(new URL(wasmUrl, location.href).href));
      }).catch(reject);
    });
  }
  async createSandbox(data) {
    const sandbox = await this._ready;
    sandbox.create(data);
  }
  async dispatchEventInSandbox(event) {
    const sandbox = await this._ready;
    setTimeout(() => sandbox.dispatchEvent(event), 0);
  }
  async destroySandbox() {
    const sandbox = await this._ready;
    sandbox.nukeSandbox();
  }
}

;// ./web/generic_signature_storage.js

const KEY_STORAGE = "pdfjs.signature";
class SignatureStorage {
  #eventBus;
  #signatures = null;
  #signal = null;
  constructor(eventBus, signal) {
    this.#eventBus = eventBus;
    this.#signal = signal;
  }
  #save() {
    localStorage.setItem(KEY_STORAGE, JSON.stringify(Object.fromEntries(this.#signatures)));
  }
  async getAll() {
    if (this.#signal) {
      window.addEventListener("storage", ({
        key
      }) => {
        if (key === KEY_STORAGE) {
          this.#signatures = null;
          this.#eventBus?.dispatch("storedsignatureschanged", {
            source: this
          });
        }
      }, {
        signal: this.#signal
      });
      this.#signal = null;
    }
    if (!this.#signatures) {
      this.#signatures = new Map();
      const data = localStorage.getItem(KEY_STORAGE);
      if (data) {
        for (const [key, value] of Object.entries(JSON.parse(data))) {
          this.#signatures.set(key, value);
        }
      }
    }
    return this.#signatures;
  }
  async isFull() {
    return (await this.size()) === 5;
  }
  async size() {
    return (await this.getAll()).size;
  }
  async create(data) {
    if (await this.isFull()) {
      return null;
    }
    const uuid = getUuid();
    this.#signatures.set(uuid, data);
    this.#save();
    return uuid;
  }
  async delete(uuid) {
    const signatures = await this.getAll();
    if (!signatures.has(uuid)) {
      return false;
    }
    signatures.delete(uuid);
    this.#save();
    return true;
  }
}

;// ./web/genericcom.js






function initCom(app) {}
class Preferences extends BasePreferences {
  async _writeToStorage(prefObj) {
    localStorage.setItem("pdfjs.preferences", JSON.stringify(prefObj));
  }
  async _readFromStorage(prefObj) {
    return {
      prefs: JSON.parse(localStorage.getItem("pdfjs.preferences"))
    };
  }
}
class ExternalServices extends BaseExternalServices {
  constructor() {
    super();
  }
  async createL10n() {
    return new genericl10n_GenericL10n(AppOptions.get("localeProperties")?.lang);
  }
  createScripting() {
    return new GenericScripting(AppOptions.get("sandboxBundleSrc"), AppOptions.get("wasmUrl"));
  }
  createSignatureStorage(eventBus, signal) {
    return new SignatureStorage(eventBus, signal);
  }
  createSignatureVerifier() {
    return null;
  }
}
class MLManager {
  async isEnabledFor(_name) {
    return false;
  }
  async deleteModel(_service) {
    return null;
  }
  isReady(_name) {
    return false;
  }
  guess(_data) {}
  toggleService(_name, _enabled) {}
}

;// ./web/new_alt_text_manager.js


class NewAltTextManager {
  #boundCancel = this.#cancel.bind(this);
  #createAutomaticallyButton;
  #currentEditor = null;
  #cancelButton;
  #descriptionContainer;
  #dialog;
  #disclaimer;
  #downloadModel;
  #downloadModelDescription;
  #eventBus;
  #firstTime = false;
  #guessedAltText;
  #hasAI = null;
  #isEditing = null;
  #imagePreview;
  #imageData;
  #isAILoading = false;
  #wasAILoading = false;
  #learnMore;
  #notNowButton;
  #overlayManager;
  #textarea;
  #title;
  #uiManager;
  #previousAltText = null;
  constructor({
    descriptionContainer,
    dialog,
    imagePreview,
    cancelButton,
    disclaimer,
    notNowButton,
    saveButton,
    textarea,
    learnMore,
    errorCloseButton,
    createAutomaticallyButton,
    downloadModel,
    downloadModelDescription,
    title
  }, overlayManager, eventBus) {
    this.#cancelButton = cancelButton;
    this.#createAutomaticallyButton = createAutomaticallyButton;
    this.#descriptionContainer = descriptionContainer;
    this.#dialog = dialog;
    this.#disclaimer = disclaimer;
    this.#notNowButton = notNowButton;
    this.#imagePreview = imagePreview;
    this.#textarea = textarea;
    this.#learnMore = learnMore;
    this.#title = title;
    this.#downloadModel = downloadModel;
    this.#downloadModelDescription = downloadModelDescription;
    this.#overlayManager = overlayManager;
    this.#eventBus = eventBus;
    dialog.addEventListener("close", this.#close.bind(this));
    dialog.addEventListener("contextmenu", event => {
      if (event.target !== this.#textarea) {
        event.preventDefault();
      }
    });
    cancelButton.addEventListener("click", this.#boundCancel);
    notNowButton.addEventListener("click", this.#boundCancel);
    saveButton.addEventListener("click", this.#save.bind(this));
    errorCloseButton.addEventListener("click", () => {
      this.#toggleError(false);
    });
    createAutomaticallyButton.addEventListener("click", async () => {
      const checked = createAutomaticallyButton.getAttribute("aria-pressed") !== "true";
      this.#currentEditor._reportTelemetry({
        action: "pdfjs.image.alt_text.ai_generation_check",
        data: {
          status: checked
        }
      });
      if (this.#uiManager) {
        const isAltTextEnabled = await this.#uiManager.mlManager.isEnabledFor("altText");
        this.#createAutomaticallyButton.disabled = true;
        if (checked && !isAltTextEnabled) {
          this.#textarea.value = "";
          this.#setProgress();
          this.#uiManager.setPreference("enableGuessAltText", true);
          await this.#uiManager.mlManager.downloadModel("altText");
          this.#setPref("enableAltTextModelDownload", true);
        } else if (!checked && isAltTextEnabled) {
          this.#uiManager.setPreference("enableGuessAltText", false);
          await this.#uiManager.mlManager.deleteModel("altText");
          this.#setPref("enableAltTextModelDownload", false);
        }
        this.#createAutomaticallyButton.disabled = false;
        await this.#uiManager.mlManager.toggleService("altText", checked);
      }
      this.#toggleGuessAltText(checked, false);
    });
    textarea.addEventListener("focus", () => {
      this.#wasAILoading = this.#isAILoading;
      this.#toggleLoading(false);
      this.#toggleTitleAndDisclaimer();
    });
    textarea.addEventListener("blur", () => {
      if (!textarea.value) {
        this.#toggleLoading(this.#wasAILoading);
      }
      this.#toggleTitleAndDisclaimer();
    });
    textarea.addEventListener("input", () => {
      this.#toggleTitleAndDisclaimer();
    });
    textarea.addEventListener("keydown", e => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && !saveButton.disabled) {
        this.#save();
      }
    });
    eventBus.on("enableguessalttext", ({
      value
    }) => {
      this.#toggleGuessAltText(value, false);
    }, internalOpt);
    this.#overlayManager.register(dialog);
    this.#learnMore.addEventListener("click", () => {
      this.#currentEditor._reportTelemetry({
        action: "pdfjs.image.alt_text.info",
        data: {
          topic: "alt_text"
        }
      });
    });
  }
  #setPref(name, value) {
    this.#eventBus.dispatch("setpreference", {
      source: this,
      name,
      value
    });
  }
  #toggleLoading(value) {
    if (!this.#uiManager || this.#isAILoading === value) {
      return;
    }
    this.#isAILoading = value;
    this.#descriptionContainer.classList.toggle("loading", value);
  }
  #toggleError(value) {
    if (!this.#uiManager) {
      return;
    }
    this.#dialog.classList.toggle("error", value);
  }
  async #toggleGuessAltText(value, isInitial) {
    if (!this.#uiManager) {
      return;
    }
    this.#dialog.classList.toggle("aiDisabled", !value);
    this.#createAutomaticallyButton.setAttribute("aria-pressed", value);
    if (value) {
      const {
        altTextLearnMoreUrl
      } = this.#uiManager.mlManager;
      if (altTextLearnMoreUrl) {
        this.#learnMore.href = altTextLearnMoreUrl;
      }
      this.#mlGuessAltText(isInitial);
    } else {
      this.#toggleLoading(false);
      this.#isAILoading = false;
      this.#toggleTitleAndDisclaimer();
    }
  }
  #toggleNotNow() {
    this.#notNowButton.classList.toggle("hidden", !this.#firstTime);
    this.#cancelButton.classList.toggle("hidden", this.#firstTime);
  }
  #toggleAI(value) {
    if (!this.#uiManager || this.#hasAI === value) {
      return;
    }
    this.#hasAI = value;
    this.#dialog.classList.toggle("noAi", !value);
    this.#toggleTitleAndDisclaimer();
  }
  #toggleTitleAndDisclaimer() {
    const visible = this.#isAILoading || this.#guessedAltText && this.#guessedAltText === this.#textarea.value;
    this.#disclaimer.hidden = !visible;
    const isEditing = this.#isAILoading || !!this.#textarea.value;
    if (this.#isEditing === isEditing) {
      return;
    }
    this.#isEditing = isEditing;
    this.#title.setAttribute("data-l10n-id", isEditing ? "pdfjs-editor-new-alt-text-dialog-edit-label" : "pdfjs-editor-new-alt-text-dialog-add-label");
  }
  async #mlGuessAltText(isInitial) {
    if (this.#isAILoading) {
      return;
    }
    if (this.#textarea.value) {
      return;
    }
    if (isInitial && this.#previousAltText !== null) {
      return;
    }
    this.#guessedAltText = this.#currentEditor.guessedAltText;
    if (this.#previousAltText === null && this.#guessedAltText) {
      this.#addAltText(this.#guessedAltText);
      return;
    }
    this.#toggleLoading(true);
    this.#toggleTitleAndDisclaimer();
    let hasError = false;
    try {
      const altText = await this.#currentEditor.mlGuessAltText(this.#imageData, false);
      if (altText) {
        this.#guessedAltText = altText;
        this.#wasAILoading = this.#isAILoading;
        if (this.#isAILoading) {
          this.#addAltText(altText);
        }
      }
    } catch (e) {
      console.error(e);
      hasError = true;
    }
    this.#toggleLoading(false);
    this.#toggleTitleAndDisclaimer();
    if (hasError && this.#uiManager) {
      this.#toggleError(true);
    }
  }
  #addAltText(altText) {
    if (!this.#uiManager || this.#textarea.value) {
      return;
    }
    this.#textarea.value = altText;
    this.#toggleTitleAndDisclaimer();
  }
  #setProgress() {
    this.#downloadModel.classList.toggle("hidden", false);
    const callback = async ({
      detail: {
        finished,
        total,
        totalLoaded
      }
    }) => {
      const ONE_MEGA_BYTES = 1e6;
      totalLoaded = Math.min(0.99 * total, totalLoaded);
      const totalSize = this.#downloadModelDescription.ariaValueMax = Math.round(total / ONE_MEGA_BYTES);
      const downloadedSize = this.#downloadModelDescription.ariaValueNow = Math.round(totalLoaded / ONE_MEGA_BYTES);
      this.#downloadModelDescription.setAttribute("data-l10n-args", JSON.stringify({
        totalSize,
        downloadedSize
      }));
      if (!finished) {
        return;
      }
      this.#eventBus.off("loadaiengineprogress", callback);
      this.#downloadModel.classList.toggle("hidden", true);
      this.#toggleAI(true);
      if (!this.#uiManager) {
        return;
      }
      const {
        mlManager
      } = this.#uiManager;
      mlManager.toggleService("altText", true);
      this.#toggleGuessAltText(await mlManager.isEnabledFor("altText"), true);
    };
    this.#eventBus.on("loadaiengineprogress", callback, internalOpt);
  }
  async editAltText(uiManager, editor, firstTime) {
    if (this.#currentEditor || !editor) {
      return;
    }
    if (firstTime && editor.hasAltTextData()) {
      editor.altTextFinish();
      return;
    }
    this.#firstTime = firstTime;
    const {
      mlManager
    } = uiManager;
    const hasAI = !!mlManager;
    this.#toggleTitleAndDisclaimer();
    if (mlManager && !mlManager.isReady("altText")) {
      if (mlManager.hasProgress) {
        this.#setProgress();
      } else {
        this.#createAutomaticallyButton.setAttribute("aria-pressed", false);
      }
    } else {
      this.#downloadModel.classList.toggle("hidden", true);
    }
    const isAltTextEnabledPromise = mlManager?.isEnabledFor("altText");
    this.#currentEditor = editor;
    this.#uiManager = uiManager;
    this.#uiManager.removeEditListeners();
    ({
      altText: this.#previousAltText
    } = editor.altTextData);
    this.#textarea.value = this.#previousAltText ?? "";
    const AI_MAX_IMAGE_DIMENSION = 224;
    const MAX_PREVIEW_DIMENSION = 180;
    let canvas, width, height;
    if (mlManager) {
      ({
        canvas,
        width,
        height,
        imageData: this.#imageData
      } = editor.copyCanvas(AI_MAX_IMAGE_DIMENSION, MAX_PREVIEW_DIMENSION, true));
      if (hasAI) {
        this.#toggleGuessAltText(await isAltTextEnabledPromise, true);
      }
    } else {
      ({
        canvas,
        width,
        height
      } = editor.copyCanvas(AI_MAX_IMAGE_DIMENSION, MAX_PREVIEW_DIMENSION, false));
    }
    canvas.setAttribute("role", "presentation");
    const {
      style
    } = canvas;
    style.width = `${width}px`;
    style.height = `${height}px`;
    this.#imagePreview.append(canvas);
    this.#toggleNotNow();
    this.#toggleAI(hasAI);
    this.#toggleError(false);
    try {
      await this.#overlayManager.open(this.#dialog);
    } catch (ex) {
      this.#close();
      throw ex;
    }
  }
  #cancel() {
    this.#currentEditor.altTextData = {
      cancel: true
    };
    const altText = this.#textarea.value.trim();
    this.#currentEditor._reportTelemetry({
      action: "pdfjs.image.alt_text.dismiss",
      data: {
        alt_text_type: altText ? "present" : "empty",
        flow: this.#firstTime ? "image_add" : "alt_text_edit"
      }
    });
    this.#currentEditor._reportTelemetry({
      action: "pdfjs.image.image_added",
      data: {
        alt_text_modal: true,
        alt_text_type: "skipped"
      }
    });
    this.#finish();
  }
  #finish() {
    this.#overlayManager.closeIfActive(this.#dialog);
  }
  #close() {
    const canvas = this.#imagePreview.firstElementChild;
    canvas.remove();
    canvas.width = canvas.height = 0;
    this.#imageData = null;
    this.#toggleLoading(false);
    this.#uiManager?.addEditListeners();
    this.#currentEditor.altTextFinish();
    this.#uiManager?.setSelected(this.#currentEditor);
    this.#currentEditor = null;
    this.#uiManager = null;
  }
  #extractWords(text) {
    return new Set(text.toLowerCase().split(/[^\p{L}\p{N}]+/gu).filter(Boolean));
  }
  #save() {
    const altText = this.#textarea.value.trim();
    this.#currentEditor.altTextData = {
      altText,
      decorative: false
    };
    this.#currentEditor.altTextData.guessedAltText = this.#guessedAltText;
    if (this.#guessedAltText && this.#guessedAltText !== altText) {
      const guessedWords = this.#extractWords(this.#guessedAltText);
      const words = this.#extractWords(altText);
      this.#currentEditor._reportTelemetry({
        action: "pdfjs.image.alt_text.user_edit",
        data: {
          total_words: guessedWords.size,
          words_removed: guessedWords.difference(words).size,
          words_added: words.difference(guessedWords).size
        }
      });
    }
    this.#currentEditor._reportTelemetry({
      action: "pdfjs.image.image_added",
      data: {
        alt_text_modal: true,
        alt_text_type: altText ? "present" : "empty"
      }
    });
    this.#currentEditor._reportTelemetry({
      action: "pdfjs.image.alt_text.save",
      data: {
        alt_text_type: altText ? "present" : "empty",
        flow: this.#firstTime ? "image_add" : "alt_text_edit"
      }
    });
    this.#finish();
  }
  destroy() {
    this.#uiManager = null;
    this.#finish();
  }
}
class ImageAltTextSettings {
  #createModelButton;
  #dialog;
  #eventBus;
  #mlManager;
  #overlayManager;
  #showAltTextDialogButton;
  constructor({
    dialog,
    createModelButton,
    learnMore,
    closeButton,
    showAltTextDialogButton
  }, overlayManager, eventBus, mlManager) {
    this.#dialog = dialog;
    this.#createModelButton = createModelButton;
    this.#showAltTextDialogButton = showAltTextDialogButton;
    this.#overlayManager = overlayManager;
    this.#eventBus = eventBus;
    this.#mlManager = mlManager;
    const {
      altTextLearnMoreUrl
    } = mlManager;
    if (altTextLearnMoreUrl) {
      learnMore.href = altTextLearnMoreUrl;
    }
    dialog.addEventListener("contextmenu", noContextMenu);
    createModelButton.addEventListener("click", async e => {
      const checked = this.#togglePref("enableGuessAltText", e);
      await (checked ? this.#download(true) : this.#delete(true));
      await mlManager.toggleService("altText", checked);
      this.#reportTelemetry({
        type: "stamp",
        action: "pdfjs.image.alt_text.settings_ai_generation_check",
        data: {
          status: checked
        }
      });
    });
    showAltTextDialogButton.addEventListener("click", e => {
      const checked = this.#togglePref("enableNewAltTextWhenAddingImage", e);
      this.#reportTelemetry({
        type: "stamp",
        action: "pdfjs.image.alt_text.settings_edit_alt_text_check",
        data: {
          status: checked
        }
      });
    });
    closeButton.addEventListener("click", this.#finish.bind(this));
    learnMore.addEventListener("click", () => {
      this.#reportTelemetry({
        type: "stamp",
        action: "pdfjs.image.alt_text.info",
        data: {
          topic: "ai_generation"
        }
      });
    });
    eventBus.on("enablealttextmodeldownload", ({
      value
    }) => {
      if (value) {
        this.#download(false);
      } else {
        this.#delete(false);
      }
    }, internalOpt);
    this.#overlayManager.register(dialog);
  }
  #reportTelemetry(data) {
    this.#eventBus.dispatch("reporttelemetry", {
      source: this,
      details: {
        type: "editing",
        data
      }
    });
  }
  async #download(isFromUI = false) {
    if (isFromUI) {
      await this.#mlManager.downloadModel("altText");
      this.#setPref("enableGuessAltText", true);
      this.#mlManager.toggleService("altText", true);
      this.#setPref("enableAltTextModelDownload", true);
    }
  }
  async #delete(isFromUI = false) {
    if (isFromUI) {
      await this.#mlManager.deleteModel("altText");
      this.#setPref("enableGuessAltText", false);
      this.#setPref("enableAltTextModelDownload", false);
    }
    this.#createModelButton.setAttribute("aria-pressed", false);
  }
  async open({
    enableGuessAltText,
    enableNewAltTextWhenAddingImage
  }) {
    const {
      enableAltTextModelDownload
    } = this.#mlManager;
    this.#createModelButton.setAttribute("aria-pressed", enableAltTextModelDownload && enableGuessAltText);
    this.#showAltTextDialogButton.setAttribute("aria-pressed", enableNewAltTextWhenAddingImage);
    await this.#overlayManager.open(this.#dialog);
    this.#reportTelemetry({
      type: "stamp",
      action: "pdfjs.image.alt_text.settings_displayed"
    });
  }
  #togglePref(name, {
    target
  }) {
    const checked = target.getAttribute("aria-pressed") !== "true";
    this.#setPref(name, checked);
    target.setAttribute("aria-pressed", checked);
    return checked;
  }
  #setPref(name, value) {
    this.#eventBus.dispatch("setpreference", {
      source: this,
      name,
      value
    });
  }
  #finish() {
    this.#overlayManager.closeIfActive(this.#dialog);
  }
}

;// ./web/alt_text_manager.js


class AltTextManager {
  #clickAC = null;
  #currentEditor = null;
  #cancelButton;
  #dialog;
  #eventBus;
  #hasUsedPointer = false;
  #optionDescription;
  #optionDecorative;
  #overlayManager;
  #saveButton;
  #textarea;
  #uiManager;
  #previousAltText = null;
  #resizeAC = null;
  #svgElement = null;
  #rectElement = null;
  #container;
  #telemetryData = null;
  constructor({
    dialog,
    optionDescription,
    optionDecorative,
    textarea,
    cancelButton,
    saveButton
  }, container, overlayManager, eventBus) {
    this.#dialog = dialog;
    this.#optionDescription = optionDescription;
    this.#optionDecorative = optionDecorative;
    this.#textarea = textarea;
    this.#cancelButton = cancelButton;
    this.#saveButton = saveButton;
    this.#overlayManager = overlayManager;
    this.#eventBus = eventBus;
    this.#container = container;
    const onUpdateUIState = this.#updateUIState.bind(this);
    dialog.addEventListener("close", this.#close.bind(this));
    dialog.addEventListener("contextmenu", event => {
      if (event.target !== this.#textarea) {
        event.preventDefault();
      }
    });
    cancelButton.addEventListener("click", this.#finish.bind(this));
    saveButton.addEventListener("click", this.#save.bind(this));
    optionDescription.addEventListener("change", onUpdateUIState);
    optionDecorative.addEventListener("change", onUpdateUIState);
    textarea.addEventListener("keydown", e => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && !saveButton.disabled) {
        this.#save();
      }
    });
    this.#overlayManager.register(dialog);
  }
  #createSVGElement() {
    if (this.#svgElement) {
      return;
    }
    const svgFactory = new DOMSVGFactory();
    const svg = this.#svgElement = svgFactory.createElement("svg");
    svg.setAttribute("width", "0");
    svg.setAttribute("height", "0");
    const defs = svgFactory.createElement("defs");
    svg.append(defs);
    const mask = svgFactory.createElement("mask");
    defs.append(mask);
    mask.setAttribute("id", "alttext-manager-mask");
    mask.setAttribute("maskContentUnits", "objectBoundingBox");
    let rect = svgFactory.createElement("rect");
    mask.append(rect);
    rect.setAttribute("fill", "white");
    rect.setAttribute("width", "1");
    rect.setAttribute("height", "1");
    rect.setAttribute("x", "0");
    rect.setAttribute("y", "0");
    rect = this.#rectElement = svgFactory.createElement("rect");
    mask.append(rect);
    rect.setAttribute("fill", "black");
    this.#dialog.append(svg);
  }
  async editAltText(uiManager, editor) {
    if (this.#currentEditor || !editor) {
      return;
    }
    this.#createSVGElement();
    this.#hasUsedPointer = false;
    this.#clickAC = new AbortController();
    const clickOpts = {
        signal: this.#clickAC.signal
      },
      onClick = this.#onClick.bind(this);
    for (const element of [this.#optionDescription, this.#optionDecorative, this.#textarea, this.#saveButton, this.#cancelButton]) {
      element.addEventListener("click", onClick, clickOpts);
    }
    const {
      altText,
      decorative
    } = editor.altTextData;
    if (decorative === true) {
      this.#optionDecorative.checked = true;
      this.#optionDescription.checked = false;
    } else {
      this.#optionDecorative.checked = false;
      this.#optionDescription.checked = true;
    }
    this.#previousAltText = this.#textarea.value = altText?.trim() || "";
    this.#updateUIState();
    this.#currentEditor = editor;
    this.#uiManager = uiManager;
    this.#uiManager.removeEditListeners();
    this.#resizeAC = new AbortController();
    this.#eventBus.on("resize", this.#setPosition.bind(this), {
      signal: this.#resizeAC.signal,
      ...internalOpt
    });
    try {
      await this.#overlayManager.open(this.#dialog);
      this.#setPosition();
    } catch (ex) {
      this.#close();
      throw ex;
    }
  }
  #setPosition() {
    if (!this.#currentEditor) {
      return;
    }
    const dialog = this.#dialog;
    const {
      style
    } = dialog;
    const {
      x: containerX,
      y: containerY,
      width: containerW,
      height: containerH
    } = this.#container.getBoundingClientRect();
    const {
      innerWidth: windowW,
      innerHeight: windowH
    } = window;
    const {
      width: dialogW,
      height: dialogH
    } = dialog.getBoundingClientRect();
    const {
      x,
      y,
      width,
      height
    } = this.#currentEditor.getClientDimensions();
    const MARGIN = 10;
    const isLTR = this.#uiManager.direction === "ltr";
    const xs = Math.max(x, containerX);
    const xe = Math.min(x + width, containerX + containerW);
    const ys = Math.max(y, containerY);
    const ye = Math.min(y + height, containerY + containerH);
    this.#rectElement.setAttribute("width", `${(xe - xs) / windowW}`);
    this.#rectElement.setAttribute("height", `${(ye - ys) / windowH}`);
    this.#rectElement.setAttribute("x", `${xs / windowW}`);
    this.#rectElement.setAttribute("y", `${ys / windowH}`);
    let left = null;
    let top = Math.max(y, 0);
    top += Math.min(windowH - (top + dialogH), 0);
    if (isLTR) {
      if (x + width + MARGIN + dialogW < windowW) {
        left = x + width + MARGIN;
      } else if (x > dialogW + MARGIN) {
        left = x - dialogW - MARGIN;
      }
    } else if (x > dialogW + MARGIN) {
      left = x - dialogW - MARGIN;
    } else if (x + width + MARGIN + dialogW < windowW) {
      left = x + width + MARGIN;
    }
    if (left === null) {
      top = null;
      left = Math.max(x, 0);
      left += Math.min(windowW - (left + dialogW), 0);
      if (y > dialogH + MARGIN) {
        top = y - dialogH - MARGIN;
      } else if (y + height + MARGIN + dialogH < windowH) {
        top = y + height + MARGIN;
      }
    }
    if (top !== null) {
      dialog.classList.add("positioned");
      if (isLTR) {
        style.left = `${left}px`;
      } else {
        style.right = `${windowW - left - dialogW}px`;
      }
      style.top = `${top}px`;
    } else {
      dialog.classList.remove("positioned");
      style.left = "";
      style.top = "";
    }
  }
  #finish() {
    this.#overlayManager.closeIfActive(this.#dialog);
  }
  #close() {
    this.#currentEditor._reportTelemetry(this.#telemetryData || {
      action: "alt_text_cancel",
      alt_text_keyboard: !this.#hasUsedPointer
    });
    this.#telemetryData = null;
    this.#removeOnClickListeners();
    this.#uiManager?.addEditListeners();
    this.#resizeAC?.abort();
    this.#resizeAC = null;
    this.#currentEditor.altTextFinish();
    this.#currentEditor = null;
    this.#uiManager = null;
  }
  #updateUIState() {
    this.#textarea.disabled = this.#optionDecorative.checked;
  }
  #save() {
    const altText = this.#textarea.value.trim();
    const decorative = this.#optionDecorative.checked;
    this.#currentEditor.altTextData = {
      altText,
      decorative
    };
    this.#telemetryData = {
      action: "alt_text_save",
      alt_text_description: !!altText,
      alt_text_edit: !!this.#previousAltText && this.#previousAltText !== altText,
      alt_text_decorative: decorative,
      alt_text_keyboard: !this.#hasUsedPointer
    };
    this.#finish();
  }
  #onClick(evt) {
    if (evt.detail === 0) {
      return;
    }
    this.#hasUsedPointer = true;
    this.#removeOnClickListeners();
  }
  #removeOnClickListeners() {
    this.#clickAC?.abort();
    this.#clickAC = null;
  }
  destroy() {
    this.#uiManager = null;
    this.#finish();
    this.#svgElement?.remove();
    this.#svgElement = this.#rectElement = null;
  }
}

;// ./web/annotation_editor_params.js


class AnnotationEditorParams {
  constructor(options, eventBus) {
    this.eventBus = eventBus;
    this.#bindListeners(options);
  }
  #bindListeners({
    editorFreeTextFontSize,
    editorFreeTextColor,
    editorInkColor,
    editorInkThickness,
    editorInkOpacity,
    editorStampAddImage,
    editorFreeHighlightThickness,
    editorHighlightShowAll,
    editorSignatureAddSignature
  }) {
    const {
      eventBus
    } = this;
    const dispatchEvent = (typeStr, value) => {
      eventBus.dispatch("switchannotationeditorparams", {
        source: this,
        type: AnnotationEditorParamsType[typeStr],
        value
      });
    };
    editorFreeTextFontSize.addEventListener("input", function () {
      dispatchEvent("FREETEXT_SIZE", this.valueAsNumber);
    });
    editorFreeTextColor.addEventListener("input", function () {
      dispatchEvent("FREETEXT_COLOR", this.value);
    });
    let updateInkColor, updateInkOpacity;
    if (FeatureTest.isAlphaColorInputSupported) {
      editorInkColor.setAttribute("alpha", "");
      editorInkOpacity.closest(".editorParamsSetter").remove();
      let currentInkColor = "#000000";
      let currentInkOpacity = 1;
      editorInkColor.addEventListener("input", function () {
        const rgba = getRGBA(this.value);
        if (!rgba) {
          return;
        }
        const [r, g, b, opacity] = rgba;
        const hex = Util.makeHexColor(r, g, b);
        currentInkColor = hex;
        currentInkOpacity = opacity;
        dispatchEvent("INK_COLOR_AND_OPACITY", {
          color: hex,
          opacity
        });
      });
      updateInkColor = value => {
        currentInkColor = value;
        const alphaHex = Util.hexNums[Math.round(currentInkOpacity * 255)];
        editorInkColor.value = currentInkColor + alphaHex;
      };
      updateInkOpacity = value => {
        currentInkOpacity = value;
        const alphaHex = Util.hexNums[Math.round(currentInkOpacity * 255)];
        editorInkColor.value = currentInkColor + alphaHex;
      };
    } else {
      editorInkColor.addEventListener("input", function () {
        dispatchEvent("INK_COLOR", this.value);
      });
      editorInkOpacity.addEventListener("input", function () {
        dispatchEvent("INK_OPACITY", this.valueAsNumber);
      });
      updateInkColor = value => {
        editorInkColor.value = value;
      };
      updateInkOpacity = value => {
        editorInkOpacity.value = value;
      };
    }
    editorInkThickness.addEventListener("input", function () {
      dispatchEvent("INK_THICKNESS", this.valueAsNumber);
    });
    editorStampAddImage.addEventListener("click", () => {
      eventBus.dispatch("reporttelemetry", {
        source: this,
        details: {
          type: "editing",
          data: {
            action: "pdfjs.image.add_image_click"
          }
        }
      });
      dispatchEvent("CREATE");
    });
    editorFreeHighlightThickness.addEventListener("input", function () {
      dispatchEvent("HIGHLIGHT_THICKNESS", this.valueAsNumber);
    });
    editorHighlightShowAll.addEventListener("click", function () {
      const checked = this.getAttribute("aria-pressed") === "true";
      this.setAttribute("aria-pressed", !checked);
      dispatchEvent("HIGHLIGHT_SHOW_ALL", !checked);
    });
    editorSignatureAddSignature.addEventListener("click", () => {
      dispatchEvent("CREATE");
    });
    eventBus.on("annotationeditorparamschanged", evt => {
      for (const [type, value] of evt.details) {
        switch (type) {
          case AnnotationEditorParamsType.FREETEXT_SIZE:
            editorFreeTextFontSize.value = value;
            break;
          case AnnotationEditorParamsType.FREETEXT_COLOR:
            editorFreeTextColor.value = value;
            break;
          case AnnotationEditorParamsType.INK_COLOR:
            updateInkColor(value);
            break;
          case AnnotationEditorParamsType.INK_THICKNESS:
            editorInkThickness.value = value;
            break;
          case AnnotationEditorParamsType.INK_OPACITY:
            updateInkOpacity(value);
            break;
          case AnnotationEditorParamsType.HIGHLIGHT_COLOR:
            eventBus.dispatch("mainhighlightcolorpickerupdatecolor", {
              source: this,
              value
            });
            break;
          case AnnotationEditorParamsType.HIGHLIGHT_THICKNESS:
            editorFreeHighlightThickness.value = value;
            break;
          case AnnotationEditorParamsType.HIGHLIGHT_FREE:
            editorFreeHighlightThickness.disabled = !value;
            break;
          case AnnotationEditorParamsType.HIGHLIGHT_SHOW_ALL:
            editorHighlightShowAll.setAttribute("aria-pressed", value);
            break;
        }
      }
    }, internalOpt);
  }
}

;// ./web/caret_browsing.js
const PRECISION = 1e-1;
class CaretBrowsingMode {
  #mainContainer;
  #toolBarHeight = 0;
  #viewerContainer;
  constructor(abortSignal, mainContainer, viewerContainer, toolbarContainer) {
    this.#mainContainer = mainContainer;
    this.#viewerContainer = viewerContainer;
    if (!toolbarContainer) {
      return;
    }
    this.#toolBarHeight = toolbarContainer.getBoundingClientRect().height;
    const toolbarObserver = new ResizeObserver(entries => {
      for (const entry of entries) {
        if (entry.target === toolbarContainer) {
          this.#toolBarHeight = Math.floor(entry.borderBoxSize[0].blockSize);
          break;
        }
      }
    });
    toolbarObserver.observe(toolbarContainer);
    abortSignal.addEventListener("abort", () => toolbarObserver.disconnect(), {
      once: true
    });
  }
  #isOnSameLine(rect1, rect2) {
    const top1 = rect1.y;
    const bot1 = rect1.bottom;
    const mid1 = rect1.y + rect1.height / 2;
    const top2 = rect2.y;
    const bot2 = rect2.bottom;
    const mid2 = rect2.y + rect2.height / 2;
    return top1 <= mid2 && mid2 <= bot1 || top2 <= mid1 && mid1 <= bot2;
  }
  #isUnderOver(rect, x, y, isUp) {
    const midY = rect.y + rect.height / 2;
    return (isUp ? y >= midY : y <= midY) && rect.x - PRECISION <= x && x <= rect.right + PRECISION;
  }
  #isVisible(rect) {
    return rect.top >= this.#toolBarHeight && rect.left >= 0 && rect.bottom <= (window.innerHeight || document.documentElement.clientHeight) && rect.right <= (window.innerWidth || document.documentElement.clientWidth);
  }
  #getCaretPosition(selection, isUp) {
    const {
      focusNode,
      focusOffset
    } = selection;
    const range = document.createRange();
    range.setStart(focusNode, focusOffset);
    range.setEnd(focusNode, focusOffset);
    const rect = range.getBoundingClientRect();
    return [rect.x, isUp ? rect.top : rect.bottom];
  }
  static #caretPositionFromPoint(x, y) {
    if (!document.caretPositionFromPoint) {
      const {
        startContainer: offsetNode,
        startOffset: offset
      } = document.caretRangeFromPoint(x, y);
      return {
        offsetNode,
        offset
      };
    }
    return document.caretPositionFromPoint(x, y);
  }
  #setCaretPositionHelper(selection, caretX, select, element, rect) {
    rect ||= element.getBoundingClientRect();
    if (caretX <= rect.x + PRECISION) {
      if (select) {
        selection.extend(element.firstChild, 0);
      } else {
        selection.setPosition(element.firstChild, 0);
      }
      return;
    }
    if (rect.right - PRECISION <= caretX) {
      const {
        lastChild
      } = element;
      if (select) {
        selection.extend(lastChild, lastChild.length);
      } else {
        selection.setPosition(lastChild, lastChild.length);
      }
      return;
    }
    const midY = rect.y + rect.height / 2;
    let caretPosition = CaretBrowsingMode.#caretPositionFromPoint(caretX, midY);
    let parentElement = caretPosition.offsetNode?.parentElement;
    if (parentElement && parentElement !== element) {
      const elementsAtPoint = document.elementsFromPoint(caretX, midY);
      const savedVisibilities = [];
      for (const el of elementsAtPoint) {
        if (el === element) {
          break;
        }
        const {
          style
        } = el;
        savedVisibilities.push([el, style.visibility]);
        style.visibility = "hidden";
      }
      caretPosition = CaretBrowsingMode.#caretPositionFromPoint(caretX, midY);
      parentElement = caretPosition.offsetNode?.parentElement;
      for (const [el, visibility] of savedVisibilities) {
        el.style.visibility = visibility;
      }
    }
    if (parentElement !== element) {
      if (select) {
        selection.extend(element.firstChild, 0);
      } else {
        selection.setPosition(element.firstChild, 0);
      }
      return;
    }
    if (select) {
      selection.extend(caretPosition.offsetNode, caretPosition.offset);
    } else {
      selection.setPosition(caretPosition.offsetNode, caretPosition.offset);
    }
  }
  #setCaretPosition(select, selection, newLineElement, newLineElementRect, caretX) {
    if (this.#isVisible(newLineElementRect)) {
      this.#setCaretPositionHelper(selection, caretX, select, newLineElement, newLineElementRect);
      return;
    }
    this.#mainContainer.addEventListener("scrollend", this.#setCaretPositionHelper.bind(this, selection, caretX, select, newLineElement, null), {
      once: true
    });
    newLineElement.scrollIntoView();
  }
  #getNodeOnNextPage(textLayer, isUp) {
    while (true) {
      const page = textLayer.closest(".page");
      const pageNumber = parseInt(page.getAttribute("data-page-number"), 10);
      const nextPage = isUp ? pageNumber - 1 : pageNumber + 1;
      textLayer = this.#viewerContainer.querySelector(`.page[data-page-number="${nextPage}"] .textLayer`);
      if (!textLayer) {
        return null;
      }
      const walker = document.createTreeWalker(textLayer, NodeFilter.SHOW_TEXT);
      const node = isUp ? walker.lastChild() : walker.firstChild();
      if (node) {
        return node;
      }
    }
  }
  moveCaret(isUp, select) {
    const selection = document.getSelection();
    if (selection.rangeCount === 0) {
      return;
    }
    const {
      focusNode
    } = selection;
    const focusElement = focusNode.nodeType !== Node.ELEMENT_NODE ? focusNode.parentElement : focusNode;
    const root = focusElement.closest(".textLayer");
    if (!root) {
      return;
    }
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    walker.currentNode = focusNode;
    const focusRect = focusElement.getBoundingClientRect();
    let newLineElement = null;
    const nodeIterator = (isUp ? walker.previousSibling : walker.nextSibling).bind(walker);
    while (nodeIterator()) {
      const element = walker.currentNode.parentElement;
      if (!this.#isOnSameLine(focusRect, element.getBoundingClientRect())) {
        newLineElement = element;
        break;
      }
    }
    if (!newLineElement) {
      const node = this.#getNodeOnNextPage(root, isUp);
      if (!node) {
        return;
      }
      if (select) {
        const lastNode = (isUp ? walker.firstChild() : walker.lastChild()) || focusNode;
        selection.extend(lastNode, isUp ? 0 : lastNode.length);
        const range = document.createRange();
        range.setStart(node, isUp ? node.length : 0);
        range.setEnd(node, isUp ? node.length : 0);
        selection.addRange(range);
        return;
      }
      const [caretX] = this.#getCaretPosition(selection, isUp);
      const {
        parentElement
      } = node;
      this.#setCaretPosition(select, selection, parentElement, parentElement.getBoundingClientRect(), caretX);
      return;
    }
    const [caretX, caretY] = this.#getCaretPosition(selection, isUp);
    const newLineElementRect = newLineElement.getBoundingClientRect();
    if (this.#isUnderOver(newLineElementRect, caretX, caretY, isUp)) {
      this.#setCaretPosition(select, selection, newLineElement, newLineElementRect, caretX);
      return;
    }
    while (nodeIterator()) {
      const element = walker.currentNode.parentElement;
      const elementRect = element.getBoundingClientRect();
      if (!this.#isOnSameLine(newLineElementRect, elementRect)) {
        break;
      }
      if (this.#isUnderOver(elementRect, caretX, caretY, isUp)) {
        this.#setCaretPosition(select, selection, element, elementRect, caretX);
        return;
      }
    }
    this.#setCaretPosition(select, selection, newLineElement, newLineElementRect, caretX);
  }
}

;// ./web/sidebar.js

const RESIZE_TIMEOUT = 400;
class Sidebar {
  #initialWidth = 0;
  #width = 0;
  #coefficient;
  #resizeTimeout = null;
  #resizer;
  #isResizerOnTheLeft;
  #isKeyboardResizing = false;
  #resizeObserver;
  #prevX = 0;
  constructor({
    sidebar,
    resizer,
    toggleButton
  }, ltr, isResizerOnTheLeft, globalAbortSignal) {
    this._sidebar = sidebar;
    this.#coefficient = ltr === isResizerOnTheLeft ? -1 : 1;
    this.#resizer = resizer;
    this.#isResizerOnTheLeft = isResizerOnTheLeft;
    const style = window.getComputedStyle(sidebar);
    this.#initialWidth = this.#width = parseFloat(style.getPropertyValue("--sidebar-width"));
    resizer.ariaValueMin = parseFloat(style.getPropertyValue("--sidebar-min-width")) || 0;
    resizer.ariaValueMax = parseFloat(style.getPropertyValue("--sidebar-max-width")) || Infinity;
    resizer.ariaValueNow = this.#width;
    this.#makeSidebarResizable();
    toggleButton.addEventListener("click", this.toggle.bind(this));
    this._isOpen = false;
    sidebar.hidden = true;
    globalAbortSignal?.addEventListener("abort", this.destroy.bind(this), {
      once: true
    });
    this.#resizeObserver = new ResizeObserver(([{
      borderBoxSize: [{
        inlineSize
      }]
    }]) => {
      if (!isNaN(this.#prevX)) {
        this.#prevX += this.#coefficient * (inlineSize - this.#width);
      }
      this.#setWidth(inlineSize);
    });
    this.#resizeObserver.observe(sidebar);
  }
  #makeSidebarResizable() {
    const sidebarStyle = this._sidebar.style;
    let pointerMoveAC;
    const cancelResize = () => {
      this.#resizeTimeout = null;
      this._sidebar.classList.remove("resizing");
      pointerMoveAC?.abort();
      pointerMoveAC = null;
      this.#isKeyboardResizing = false;
      this.onStopResizing();
      this.#prevX = NaN;
    };
    this.#resizer.addEventListener("pointerdown", e => {
      if (pointerMoveAC) {
        cancelResize();
        return;
      }
      this.onStartResizing();
      const {
        clientX
      } = e;
      stopEvent(e);
      this.#prevX = clientX;
      pointerMoveAC = new AbortController();
      const {
        signal
      } = pointerMoveAC;
      const sidebar = this._sidebar;
      sidebar.classList.add("resizing");
      const parentStyle = sidebar.parentElement.style;
      parentStyle.minWidth = 0;
      window.addEventListener("contextmenu", noContextMenu, {
        signal
      });
      window.addEventListener("pointermove", ev => {
        if (!pointerMoveAC || Math.abs(ev.clientX - this.#prevX) < 1) {
          return;
        }
        stopEvent(ev);
        sidebarStyle.width = `${Math.round(this.#width + this.#coefficient * (ev.clientX - this.#prevX))}px`;
      }, {
        signal,
        capture: true
      });
      window.addEventListener("blur", cancelResize, {
        signal
      });
      window.addEventListener("pointerup", ev => {
        if (pointerMoveAC) {
          cancelResize();
          stopEvent(ev);
        }
      }, {
        signal
      });
    });
    this.#resizer.addEventListener("keydown", e => {
      const {
        key
      } = e;
      const isArrowLeft = key === "ArrowLeft";
      if (isArrowLeft || key === "ArrowRight") {
        if (!this.#isKeyboardResizing) {
          this._sidebar.classList.add("resizing");
          this.#isKeyboardResizing = true;
          this.onStartResizing();
        }
        const base = e.ctrlKey || e.metaKey ? 10 : 1;
        const dx = base * (isArrowLeft ? -1 : 1);
        clearTimeout(this.#resizeTimeout);
        this.#resizeTimeout = setTimeout(cancelResize, RESIZE_TIMEOUT);
        sidebarStyle.width = `${Math.round(this.#width + this.#coefficient * dx)}px`;
        stopEvent(e);
      }
    });
  }
  #setWidth(newWidth) {
    this.#width = newWidth;
    this.#resizer.ariaValueNow = Math.round(newWidth);
    if (this.#isResizerOnTheLeft) {
      this._sidebar.parentElement.style.insetInlineStart = `${(this.#initialWidth - newWidth).toFixed(3)}px`;
    }
    this.onResizing(newWidth);
  }
  get width() {
    return this.#width;
  }
  set width(newWidth) {
    this._sidebar.style.width = `${newWidth}px`;
  }
  onStartResizing() {}
  onStopResizing() {}
  onResizing(_newWidth) {}
  toggle(visibility = !this._isOpen) {
    this._sidebar.hidden = !(this._isOpen = visibility);
  }
  destroy() {
    this.#resizeObserver?.disconnect();
    this.#resizeObserver = null;
  }
}

;// ./web/comment_manager.js



class CommentManager {
  #dialog;
  #popup;
  #sidebar;
  static #hasForcedColors = null;
  constructor(commentDialog, sidebar, eventBus, linkService, overlayManager, ltr, hasForcedColors, globalAbortSignal) {
    const dateFormat = new Intl.DateTimeFormat(undefined, {
      dateStyle: "long"
    });
    this.dialogElement = commentDialog.dialog;
    this.#dialog = new CommentDialog(commentDialog, overlayManager, eventBus, ltr);
    this.#popup = new CommentPopup(eventBus, dateFormat, ltr, this.dialogElement);
    this.#sidebar = new CommentSidebar(sidebar, eventBus, linkService, this.#popup, dateFormat, ltr, globalAbortSignal);
    this.#popup.sidebar = this.#sidebar;
    CommentManager.#hasForcedColors = hasForcedColors;
  }
  setSidebarUiManager(uiManager) {
    this.#sidebar.setUIManager(uiManager);
  }
  showSidebar(annotations) {
    this.#sidebar.show(annotations);
  }
  hideSidebar() {
    this.#sidebar.hide();
  }
  removeComments(ids) {
    this.#sidebar.removeComments(ids);
  }
  selectComment(id) {
    this.#sidebar.selectComment(null, id);
  }
  addComment(annotation) {
    this.#sidebar.addComment(annotation);
  }
  updateComment(annotation) {
    this.#sidebar.updateComment(annotation);
  }
  toggleCommentPopup(editor, isSelected, visibility, isEditable) {
    if (isSelected) {
      this.selectComment(editor.uid);
    }
    this.#popup.toggle(editor, isSelected, visibility, isEditable);
  }
  destroyPopup() {
    this.#popup.destroy();
  }
  updatePopupColor(editor) {
    this.#popup.updateColor(editor);
  }
  showDialog(uiManager, editor, posX, posY, options) {
    return this.#dialog.open(uiManager, editor, posX, posY, options);
  }
  makeCommentColor(color, opacity) {
    return CommentManager._makeCommentColor(color, opacity);
  }
  static _makeCommentColor(color, opacity) {
    return this.#hasForcedColors ? null : findContrastColor(applyOpacity(color, opacity ?? 1), CSSConstants.commentForegroundColor);
  }
  destroy() {
    this.#dialog.destroy();
    this.#sidebar.hide();
    this.#popup.destroy();
  }
}
class CommentSidebar extends Sidebar {
  #annotations = null;
  #eventBus;
  #boundCommentClick = this.#commentClick.bind(this);
  #boundCommentKeydown = this.#commentKeydown.bind(this);
  #closeButton;
  #commentsList;
  #commentCount;
  #dateFormat;
  #sidebarTitle;
  #learnMoreUrl;
  #linkService;
  #popup;
  #elementsToAnnotations = null;
  #idsToElements = null;
  #uiManager = null;
  constructor({
    learnMoreUrl,
    sidebar,
    sidebarResizer,
    commentsList,
    commentCount,
    sidebarTitle,
    closeButton,
    commentToolbarButton
  }, eventBus, linkService, popup, dateFormat, ltr, globalAbortSignal) {
    super({
      sidebar,
      resizer: sidebarResizer,
      toggleButton: commentToolbarButton
    }, ltr, true, globalAbortSignal);
    this.#sidebarTitle = sidebarTitle;
    this.#commentsList = commentsList;
    this.#commentCount = commentCount;
    this.#learnMoreUrl = learnMoreUrl;
    this.#linkService = linkService;
    this.#closeButton = closeButton;
    this.#popup = popup;
    this.#dateFormat = dateFormat;
    this.#eventBus = eventBus;
    closeButton.addEventListener("click", () => {
      eventBus.dispatch("switchannotationeditormode", {
        source: this,
        mode: AnnotationEditorType.NONE
      });
    });
    const keyDownCallback = e => {
      if (e.key === "ArrowDown" || e.key === "Home" || e.key === "F6") {
        this.#commentsList.firstElementChild.focus();
        stopEvent(e);
      } else if (e.key === "ArrowUp" || e.key === "End") {
        this.#commentsList.lastElementChild.focus();
        stopEvent(e);
      }
    };
    commentToolbarButton.addEventListener("keydown", keyDownCallback);
    sidebar.addEventListener("keydown", keyDownCallback);
  }
  setUIManager(uiManager) {
    this.#uiManager = uiManager;
  }
  show(annotations) {
    this.#elementsToAnnotations = new WeakMap();
    this.#idsToElements = new Map();
    this.#annotations = annotations;
    annotations.sort(this.#sortComments.bind(this));
    if (annotations.length !== 0) {
      const fragment = document.createDocumentFragment();
      for (const annotation of annotations) {
        fragment.append(this.#createCommentElement(annotation));
      }
      this.#setCommentsCount(fragment);
      this.#commentsList.append(fragment);
    } else {
      this.#setCommentsCount();
    }
    this._sidebar.hidden = false;
    this.#eventBus.dispatch("reporttelemetry", {
      source: this,
      details: {
        type: "commentSidebar",
        data: {
          numberOfAnnotations: annotations.length
        }
      }
    });
  }
  hide() {
    this._sidebar.hidden = true;
    this.#commentsList.replaceChildren();
    this.#elementsToAnnotations = null;
    this.#idsToElements = null;
    this.#annotations = null;
  }
  removeComments(ids) {
    if (ids.length === 0 || !this.#idsToElements) {
      return;
    }
    if (new Set(this.#idsToElements.keys()).isSubsetOf(new Set(ids))) {
      this.#removeAll();
      return;
    }
    for (const id of ids) {
      this.#removeComment(id);
    }
  }
  focusComment(id) {
    const element = this.#idsToElements.get(id);
    if (!element) {
      return;
    }
    this._sidebar.scrollTop = element.offsetTop - this._sidebar.offsetTop;
    for (const el of this.#commentsList.children) {
      el.classList.toggle("selected", el === element);
    }
  }
  updateComment(annotation) {
    if (!this.#idsToElements) {
      return;
    }
    const {
      id,
      creationDate,
      modificationDate,
      richText,
      contentsObj,
      popupRef
    } = annotation;
    if (!popupRef || !richText && !contentsObj?.str) {
      this.#removeComment(id);
    }
    const element = this.#idsToElements.get(id);
    if (!element) {
      return;
    }
    const prevAnnotation = this.#elementsToAnnotations.get(element);
    let index = binarySearchFirstItem(this.#annotations, a => this.#sortComments(a, prevAnnotation) >= 0);
    if (index >= this.#annotations.length) {
      return;
    }
    this.#setDate(element.firstElementChild, modificationDate || creationDate);
    this.#setText(element.lastElementChild, richText, contentsObj);
    this.#annotations.splice(index, 1);
    index = binarySearchFirstItem(this.#annotations, a => this.#sortComments(a, annotation) >= 0);
    this.#annotations.splice(index, 0, annotation);
    if (index >= this.#commentsList.children.length) {
      this.#commentsList.append(element);
    } else {
      this.#commentsList.insertBefore(element, this.#commentsList.children[index]);
    }
  }
  #removeComment(id) {
    const element = this.#idsToElements?.get(id);
    if (!element) {
      return;
    }
    const annotation = this.#elementsToAnnotations.get(element);
    const index = binarySearchFirstItem(this.#annotations, a => this.#sortComments(a, annotation) >= 0);
    if (index >= this.#annotations.length) {
      return;
    }
    this.#annotations.splice(index, 1);
    element.remove();
    this.#idsToElements.delete(id);
    this.#setCommentsCount();
  }
  #removeAll() {
    this.#commentsList.replaceChildren();
    this.#elementsToAnnotations = new WeakMap();
    this.#idsToElements.clear();
    this.#annotations.length = 0;
    this.#setCommentsCount();
  }
  selectComment(element, id = null) {
    if (!this.#idsToElements) {
      return;
    }
    const hasNoElement = !element;
    element ||= this.#idsToElements.get(id);
    for (const el of this.#commentsList.children) {
      el.classList.toggle("selected", el === element);
    }
    if (hasNoElement) {
      element?.scrollIntoView({
        behavior: "instant",
        block: "center"
      });
    }
  }
  addComment(annotation) {
    if (this.#idsToElements?.has(annotation.id)) {
      return;
    }
    const {
      popupRef,
      contentsObj
    } = annotation;
    if (!popupRef || !contentsObj?.str) {
      return;
    }
    const commentItem = this.#createCommentElement(annotation);
    if (this.#annotations.length === 0) {
      this.#commentsList.replaceChildren(commentItem);
      this.#annotations.push(annotation);
      this.#setCommentsCount();
      return;
    }
    const index = binarySearchFirstItem(this.#annotations, a => this.#sortComments(a, annotation) >= 0);
    this.#annotations.splice(index, 0, annotation);
    if (index >= this.#commentsList.children.length) {
      this.#commentsList.append(commentItem);
    } else {
      this.#commentsList.insertBefore(commentItem, this.#commentsList.children[index]);
    }
    this.#setCommentsCount();
  }
  #setCommentsCount(container = this.#commentsList) {
    const count = this.#idsToElements.size;
    this.#sidebarTitle.setAttribute("data-l10n-args", JSON.stringify({
      count
    }));
    this.#commentCount.textContent = count;
    if (count === 0) {
      container.append(this.#createZeroCommentElement());
    }
  }
  #createZeroCommentElement() {
    const commentItem = document.createElement("li");
    commentItem.classList.add("sidebarComment", "noComments");
    const textDiv = document.createElement("div");
    textDiv.className = "sidebarCommentText";
    textDiv.setAttribute("data-l10n-id", "pdfjs-editor-comments-sidebar-no-comments1");
    commentItem.append(textDiv);
    if (this.#learnMoreUrl) {
      const a = document.createElement("a");
      a.setAttribute("data-l10n-id", "pdfjs-editor-comments-sidebar-no-comments-link");
      a.href = this.#learnMoreUrl;
      a.target = "_blank";
      a.rel = "noopener noreferrer";
      commentItem.append(a);
    }
    return commentItem;
  }
  #setDate(element, date) {
    date = PDFDateString.toDateObject(date);
    element.dateTime = date.toISOString();
    element.textContent = this.#dateFormat.format(date);
  }
  #setText(element, richText, contentsObj) {
    element.replaceChildren();
    const html = richText?.str && (!contentsObj?.str || richText.str === contentsObj.str) ? richText.html : contentsObj?.str;
    renderRichText({
      html,
      dir: contentsObj?.dir || "auto",
      className: "richText"
    }, element);
  }
  #createCommentElement(annotation) {
    const {
      id,
      creationDate,
      modificationDate,
      richText,
      contentsObj,
      color,
      opacity
    } = annotation;
    const commentItem = document.createElement("li");
    commentItem.role = "button";
    commentItem.className = "sidebarComment";
    commentItem.tabIndex = -1;
    commentItem.style.backgroundColor = color && CommentManager._makeCommentColor(color, opacity) || "";
    const dateDiv = document.createElement("time");
    this.#setDate(dateDiv, modificationDate || creationDate);
    const textDiv = document.createElement("div");
    textDiv.className = "sidebarCommentText";
    this.#setText(textDiv, richText, contentsObj);
    commentItem.append(dateDiv, textDiv);
    commentItem.addEventListener("click", this.#boundCommentClick);
    commentItem.addEventListener("keydown", this.#boundCommentKeydown);
    this.#elementsToAnnotations.set(commentItem, annotation);
    this.#idsToElements.set(id, commentItem);
    return commentItem;
  }
  async #commentClick({
    currentTarget
  }) {
    if (currentTarget.classList.contains("selected")) {
      currentTarget.classList.remove("selected");
      this.#popup._hide();
      return;
    }
    const annotation = this.#elementsToAnnotations.get(currentTarget);
    if (!annotation) {
      return;
    }
    this.#popup._hide();
    const {
      id,
      pageIndex,
      rect
    } = annotation;
    const pageNumber = pageIndex + 1;
    const pageVisiblePromise = this.#uiManager?.waitForEditorsRendered(pageNumber);
    this.#linkService?.goToXY(pageNumber, rect[0], rect[3], {
      center: "both"
    });
    this.selectComment(currentTarget);
    await pageVisiblePromise;
    this.#uiManager?.selectComment(pageIndex, id);
  }
  #commentKeydown(e) {
    const {
      key,
      currentTarget
    } = e;
    switch (key) {
      case "ArrowDown":
        (currentTarget.nextElementSibling || this.#commentsList.firstElementChild).focus();
        stopEvent(e);
        break;
      case "ArrowUp":
        (currentTarget.previousElementSibling || this.#commentsList.lastElementChild).focus();
        stopEvent(e);
        break;
      case "Home":
        this.#commentsList.firstElementChild.focus();
        stopEvent(e);
        break;
      case "End":
        this.#commentsList.lastElementChild.focus();
        stopEvent(e);
        break;
      case "Enter":
      case " ":
        this.#commentClick(e);
        stopEvent(e);
        break;
      case "ShiftTab":
        this.#closeButton.focus();
        stopEvent(e);
        break;
    }
  }
  #sortComments(a, b) {
    const dateA = PDFDateString.toDateObject(a.modificationDate || a.creationDate);
    const dateB = PDFDateString.toDateObject(b.modificationDate || b.creationDate);
    if (dateA !== dateB) {
      if (dateA !== null && dateB !== null) {
        return dateB - dateA;
      }
      return dateA !== null ? -1 : 1;
    }
    if (a.pageIndex !== b.pageIndex) {
      return a.pageIndex - b.pageIndex;
    }
    if (a.rect[3] !== b.rect[3]) {
      return b.rect[3] - a.rect[3];
    }
    if (a.rect[0] !== b.rect[0]) {
      return a.rect[0] - b.rect[0];
    }
    if (a.rect[1] !== b.rect[1]) {
      return b.rect[1] - a.rect[1];
    }
    return a.rect[2] !== b.rect[2] ? a.rect[2] - b.rect[2] : a.id.localeCompare(b.id);
  }
}
class CommentDialog {
  #dialog;
  #editor;
  #overlayManager;
  #previousText = "";
  #commentText = "";
  #textInput;
  #title;
  #saveButton;
  #saveButtonLabel;
  #uiManager;
  #prevDragX = 0;
  #prevDragY = 0;
  #dialogX = 0;
  #dialogY = 0;
  #isLTR;
  #eventBus;
  constructor({
    dialog,
    toolbar,
    title,
    textInput,
    cancelButton,
    saveButton
  }, overlayManager, eventBus, ltr) {
    this.#dialog = dialog;
    this.#textInput = textInput;
    this.#overlayManager = overlayManager;
    this.#eventBus = eventBus;
    this.#saveButton = saveButton;
    this.#saveButtonLabel = saveButton.firstElementChild;
    this.#title = title;
    this.#isLTR = ltr;
    const finishBound = this.#finish.bind(this);
    dialog.addEventListener("close", finishBound);
    dialog.addEventListener("contextmenu", e => {
      if (e.target !== this.#textInput) {
        e.preventDefault();
      }
    });
    cancelButton.addEventListener("click", finishBound);
    saveButton.addEventListener("click", this.#save.bind(this));
    textInput.addEventListener("input", () => {
      saveButton.disabled = textInput.value === this.#previousText;
    });
    textInput.addEventListener("keydown", e => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter" && !saveButton.disabled) {
        this.#save();
      }
    });
    let pointerMoveAC;
    const cancelDrag = () => {
      dialog.classList.remove("dragging");
      pointerMoveAC?.abort();
      pointerMoveAC = null;
    };
    toolbar.addEventListener("pointerdown", e => {
      if (pointerMoveAC) {
        cancelDrag();
        return;
      }
      const {
        clientX,
        clientY
      } = e;
      stopEvent(e);
      this.#prevDragX = clientX;
      this.#prevDragY = clientY;
      pointerMoveAC = new AbortController();
      const {
        signal
      } = pointerMoveAC;
      const {
        innerHeight,
        innerWidth
      } = window;
      dialog.classList.add("dragging");
      window.addEventListener("pointermove", ev => {
        if (!pointerMoveAC) {
          return;
        }
        const {
          clientX: x,
          clientY: y
        } = ev;
        this.#setPosition(this.#dialogX + (x - this.#prevDragX) / innerWidth, this.#dialogY + (y - this.#prevDragY) / innerHeight);
        this.#prevDragX = x;
        this.#prevDragY = y;
        stopEvent(ev);
      }, {
        signal
      });
      window.addEventListener("blur", cancelDrag, {
        signal
      });
      window.addEventListener("pointerup", ev => {
        if (pointerMoveAC) {
          cancelDrag();
          stopEvent(ev);
        }
      }, {
        signal
      });
    });
    overlayManager.register(dialog);
  }
  async open(uiManager, editor, posX, posY, options) {
    if (editor) {
      this.#uiManager = uiManager;
      this.#editor = editor;
    }
    const {
      contentsObj: {
        str
      },
      color,
      opacity
    } = editor.getData();
    const {
      style: dialogStyle
    } = this.#dialog;
    if (color) {
      dialogStyle.backgroundColor = CommentManager._makeCommentColor(color, opacity);
      dialogStyle.borderColor = Util.makeHexColor(...color);
    } else {
      dialogStyle.backgroundColor = dialogStyle.borderColor = "";
    }
    this.#commentText = str || "";
    const textInput = this.#textInput;
    textInput.value = this.#previousText = this.#commentText;
    if (str) {
      this.#title.setAttribute("data-l10n-id", "pdfjs-editor-edit-comment-dialog-title-when-editing");
      this.#saveButtonLabel.setAttribute("data-l10n-id", "pdfjs-editor-edit-comment-dialog-save-button-when-editing");
    } else {
      this.#title.setAttribute("data-l10n-id", "pdfjs-editor-edit-comment-dialog-title-when-adding");
      this.#saveButtonLabel.setAttribute("data-l10n-id", "pdfjs-editor-edit-comment-dialog-save-button-when-adding");
    }
    if (options?.height) {
      textInput.style.height = `${options.height}px`;
    }
    this.#uiManager?.removeEditListeners();
    this.#saveButton.disabled = true;
    const parentDimensions = options?.parentDimensions;
    const {
      innerHeight,
      innerWidth
    } = window;
    if (editor.hasDefaultPopupPosition()) {
      const {
        dialogWidth,
        dialogHeight
      } = this._dialogDimensions;
      if (parentDimensions) {
        if (this.#isLTR && posX + dialogWidth > Math.min(parentDimensions.x + parentDimensions.width, innerWidth)) {
          const buttonWidth = this.#editor.commentButtonWidth;
          posX -= dialogWidth - buttonWidth * parentDimensions.width;
        } else if (!this.#isLTR) {
          const buttonWidth = this.#editor.commentButtonWidth * parentDimensions.width;
          if (posX - dialogWidth < Math.max(0, parentDimensions.x)) {
            posX = Math.max(0, posX);
          } else {
            posX -= dialogWidth - buttonWidth;
          }
        }
      }
      const height = Math.max(dialogHeight, options?.height || 0);
      if (posY + height > innerHeight) {
        posY = innerHeight - height;
      }
      if (posY < 0) {
        posY = 0;
      }
    }
    posX = MathClamp(posX / innerWidth, 0, 1);
    posY = MathClamp(posY / innerHeight, 0, 1);
    this.#setPosition(posX, posY);
    await this.#overlayManager.open(this.#dialog);
    textInput.focus();
  }
  async #save() {
    this.#editor.comment = this.#textInput.value;
    this.#finish();
  }
  get _dialogDimensions() {
    const dialog = this.#dialog;
    const {
      style
    } = dialog;
    style.opacity = "0";
    style.display = "block";
    const {
      width,
      height
    } = dialog.getBoundingClientRect();
    style.opacity = style.display = "";
    return shadow(this, "_dialogDimensions", {
      dialogWidth: width,
      dialogHeight: height
    });
  }
  #setPosition(x, y) {
    this.#dialogX = x;
    this.#dialogY = y;
    const {
      style
    } = this.#dialog;
    style.left = `${100 * x}%`;
    style.top = `${100 * y}%`;
  }
  #finish() {
    if (!this.#editor) {
      return;
    }
    const edited = this.#textInput.value !== this.#commentText;
    this.#eventBus.dispatch("reporttelemetry", {
      source: this,
      details: {
        type: "comment",
        data: {
          edited
        }
      }
    });
    this.#editor?.focusCommentButton();
    this.#editor = null;
    this.#textInput.value = this.#previousText = this.#commentText = "";
    this.#overlayManager.closeIfActive(this.#dialog);
    this.#textInput.style.height = "";
    this.#uiManager?.addEditListeners();
    this.#uiManager = null;
  }
  destroy() {
    this.#uiManager = null;
    this.#editor = null;
    this.#finish();
  }
}
class CommentPopup {
  #buttonsContainer = null;
  #eventBus;
  #commentDialog;
  #dateFormat;
  #editor = null;
  #isLTR;
  #container = null;
  #text = null;
  #time = null;
  #prevDragX = 0;
  #prevDragY = 0;
  #posX = 0;
  #posY = 0;
  #previousFocusedElement = null;
  #selected = false;
  #visible = false;
  constructor(eventBus, dateFormat, ltr, commentDialog) {
    this.#eventBus = eventBus;
    this.#dateFormat = dateFormat;
    this.#isLTR = ltr;
    this.#commentDialog = commentDialog;
    this.sidebar = null;
  }
  get _popupWidth() {
    const container = this.#createPopup();
    const {
      style
    } = container;
    style.opacity = "0";
    style.display = "block";
    document.body.append(container);
    const width = container.getBoundingClientRect().width;
    container.remove();
    style.opacity = style.display = "";
    return shadow(this, "_popupWidth", width);
  }
  #createPopup() {
    if (this.#container) {
      return this.#container;
    }
    const container = this.#container = document.createElement("div");
    container.className = "commentPopup";
    container.id = "commentPopup";
    container.tabIndex = -1;
    container.role = "dialog";
    container.ariaModal = "false";
    container.addEventListener("contextmenu", noContextMenu);
    container.addEventListener("keydown", e => {
      if (e.key === "Escape") {
        this.toggle(this.#editor, true, false);
        this.#previousFocusedElement?.focus();
        stopEvent(e);
      }
    });
    container.addEventListener("click", () => {
      container.focus();
    });
    const top = document.createElement("div");
    top.className = "commentPopupTop";
    const time = this.#time = document.createElement("time");
    time.className = "commentPopupTime";
    const buttons = this.#buttonsContainer = document.createElement("div");
    buttons.className = "commentPopupButtons";
    const edit = document.createElement("button");
    edit.classList.add("commentPopupEdit", "toolbarButton");
    edit.tabIndex = 0;
    edit.setAttribute("data-l10n-id", "pdfjs-editor-edit-comment-popup-button");
    edit.ariaHasPopup = "dialog";
    edit.ariaControlsElements = [this.#commentDialog];
    const editLabel = document.createElement("span");
    editLabel.setAttribute("data-l10n-id", "pdfjs-editor-edit-comment-popup-button-label");
    edit.append(editLabel);
    edit.addEventListener("click", () => {
      const editor = this.#editor;
      const height = parseFloat(getComputedStyle(this.#text).height);
      this.toggle(editor, true, false);
      editor.editComment({
        height
      });
    });
    edit.addEventListener("contextmenu", noContextMenu);
    const del = document.createElement("button");
    del.classList.add("commentPopupDelete", "toolbarButton");
    del.tabIndex = 0;
    del.setAttribute("data-l10n-id", "pdfjs-editor-delete-comment-popup-button");
    const delLabel = document.createElement("span");
    delLabel.setAttribute("data-l10n-id", "pdfjs-editor-delete-comment-popup-button-label");
    del.append(delLabel);
    del.addEventListener("click", () => {
      this.#eventBus.dispatch("reporttelemetry", {
        source: this,
        details: {
          type: "comment",
          data: {
            deleted: true
          }
        }
      });
      const editor = this.#editor;
      const savedData = editor.comment;
      this.destroy();
      if (savedData?.text) {
        editor._uiManager.deleteComment(editor, savedData);
      } else {
        editor.comment = null;
      }
      editor.focus();
    });
    del.addEventListener("contextmenu", noContextMenu);
    buttons.append(edit, del);
    top.append(time, buttons);
    const separator = document.createElement("hr");
    const text = this.#text = document.createElement("div");
    text.className = "commentPopupText";
    container.append(top, separator, text);
    let pointerMoveAC;
    const cancelDrag = () => {
      container.classList.remove("dragging");
      pointerMoveAC?.abort();
      pointerMoveAC = null;
    };
    top.addEventListener("pointerdown", e => {
      if (pointerMoveAC) {
        cancelDrag();
        return;
      }
      const {
        target,
        clientX,
        clientY
      } = e;
      if (buttons.contains(target)) {
        return;
      }
      stopEvent(e);
      const {
        width: parentWidth,
        height: parentHeight
      } = this.#editor.parentBoundingClientRect;
      this.#prevDragX = clientX;
      this.#prevDragY = clientY;
      pointerMoveAC = new AbortController();
      const {
        signal
      } = pointerMoveAC;
      container.classList.add("dragging");
      window.addEventListener("pointermove", ev => {
        if (!pointerMoveAC) {
          return;
        }
        const {
          clientX: x,
          clientY: y
        } = ev;
        this.#setPosition(this.#posX + (x - this.#prevDragX) / parentWidth, this.#posY + (y - this.#prevDragY) / parentHeight, false);
        this.#prevDragX = x;
        this.#prevDragY = y;
        stopEvent(ev);
      }, {
        signal
      });
      window.addEventListener("blur", cancelDrag, {
        signal
      });
      window.addEventListener("pointerup", ev => {
        if (pointerMoveAC) {
          cancelDrag();
          stopEvent(ev);
        }
      }, {
        signal
      });
    });
    return container;
  }
  updateColor(editor) {
    if (this.#editor !== editor || !this.#visible) {
      return;
    }
    const {
      color,
      opacity
    } = editor.getData();
    this.#container.style.backgroundColor = color && CommentManager._makeCommentColor(color, opacity) || "";
  }
  _hide(editor) {
    const container = this.#createPopup();
    container.classList.toggle("hidden", true);
    container.classList.toggle("selected", false);
    (editor || this.#editor)?.setCommentButtonStates({
      selected: false,
      hasPopup: false
    });
    this.#editor = null;
    this.#selected = false;
    this.#visible = false;
    this.#text.replaceChildren();
    this.sidebar.selectComment(null);
  }
  toggle(editor, isSelected, visibility = undefined, isEditable = true) {
    if (!editor) {
      this.destroy();
      return;
    }
    if (isSelected) {
      visibility ??= this.#editor === editor ? !this.#selected || !this.#visible : true;
    } else {
      if (this.#selected) {
        return;
      }
      visibility ??= !this.#visible;
    }
    if (!visibility) {
      this._hide(editor);
      return;
    }
    this.#visible = true;
    if (this.#editor !== editor) {
      this.#editor?.setCommentButtonStates({
        selected: false,
        hasPopup: false
      });
    }
    const container = this.#createPopup();
    this.#buttonsContainer.classList.toggle("hidden", !isEditable);
    container.classList.toggle("hidden", false);
    container.classList.toggle("selected", isSelected);
    this.#selected = isSelected;
    this.#editor = editor;
    editor.setCommentButtonStates({
      selected: isSelected,
      hasPopup: true
    });
    const {
      contentsObj,
      richText,
      creationDate,
      modificationDate,
      color,
      opacity
    } = editor.getData();
    container.style.backgroundColor = color && CommentManager._makeCommentColor(color, opacity) || "";
    this.#text.replaceChildren();
    const html = richText?.str && (!contentsObj?.str || richText.str === contentsObj.str) ? richText.html : contentsObj?.str;
    if (html) {
      renderRichText({
        html,
        dir: contentsObj?.dir || "auto",
        className: "richText"
      }, this.#text);
    }
    this.#time.textContent = this.#dateFormat.format(PDFDateString.toDateObject(modificationDate || creationDate));
    this.#setPosition(...editor.commentPopupPosition, editor.hasDefaultPopupPosition());
    editor.elementBeforePopup.after(container);
    container.addEventListener("focus", ({
      relatedTarget
    }) => {
      this.#previousFocusedElement = relatedTarget;
    }, {
      once: true
    });
    if (isSelected) {
      setTimeout(() => container.focus(), 0);
    }
  }
  #setPosition(x, y, correctPosition) {
    if (!correctPosition) {
      this.#editor.commentPopupPosition = [x, y];
    } else {
      const parentRect = this.#editor.parentBoundingClientRect;
      const widthRatio = this._popupWidth / parentRect.width;
      if (this.#isLTR && x + widthRatio > 1 || !this.#isLTR && x - widthRatio >= 0) {
        const buttonWidth = this.#editor.commentButtonWidth;
        x -= widthRatio - buttonWidth;
      }
      const margin = 0.01;
      if (this.#isLTR) {
        x = Math.max(x, -parentRect.x / parentRect.width + margin);
      } else {
        x = Math.min(x, (window.innerWidth - parentRect.x) / parentRect.width - widthRatio - margin);
      }
    }
    this.#posX = x;
    this.#posY = y;
    const {
      style
    } = this.#container;
    style.left = `${100 * x}%`;
    style.top = `${100 * y}%`;
  }
  destroy() {
    this._hide();
    this.#container?.remove();
    this.#container = this.#text = this.#time = null;
    this.#prevDragX = this.#prevDragY = Infinity;
    this.#posX = this.#posY = 0;
    this.#previousFocusedElement = null;
  }
}

;// ./web/base_download_manager.js

class BaseDownloadManager {
  #openBlobUrls = new WeakMap();
  _triggerDownload(blobUrl, originalUrl, filename, isAttachment = false, isModified = false) {
    throw new Error("Not implemented: _triggerDownload");
  }
  _getOpenDataUrl(blobUrl, filename, dest = null) {
    throw new Error("Not implemented: _getOpenDataUrl");
  }
  downloadData(data, filename, contentType) {
    const blobUrl = URL.createObjectURL(new Blob([data], {
      type: contentType
    }));
    this._triggerDownload(blobUrl, blobUrl, filename, true);
  }
  openOrDownloadData(data, filename, dest = null) {
    const isPdfData = isPdfFile(filename);
    const contentType = isPdfData ? "application/pdf" : "";
    if (isPdfData) {
      const blobUrl = this.#openBlobUrls.getOrInsertComputed(data, () => URL.createObjectURL(new Blob([data], {
        type: contentType
      })));
      try {
        const viewerUrl = this._getOpenDataUrl(blobUrl, filename, dest);
        window.open(viewerUrl);
        return true;
      } catch (ex) {
        console.error("openOrDownloadData:", ex);
        URL.revokeObjectURL(blobUrl);
        this.#openBlobUrls.delete(data);
      }
    }
    this.downloadData(data, filename, contentType);
    return false;
  }
  download(data, url, filename, isModified = false) {
    const blobUrl = data ? URL.createObjectURL(new Blob([data], {
      type: "application/pdf"
    })) : null;
    this._triggerDownload(blobUrl, url, filename, false, isModified);
  }
}

;// ./web/download_manager.js


class DownloadManager extends BaseDownloadManager {
  _triggerDownload(blobUrl, originalUrl, filename, isAttachment = false) {
    if (!blobUrl && !isAttachment) {
      if (!createValidAbsoluteUrl(originalUrl, "http://example.com")) {
        throw new Error(`_triggerDownload - not a valid URL: ${originalUrl}`);
      }
      blobUrl = originalUrl + "#pdfjs.action=download";
    }
    const a = document.createElement("a");
    a.href = blobUrl;
    a.target = "_parent";
    if ("download" in a) {
      a.download = filename;
    }
    (document.body || document.documentElement).append(a);
    a.click();
    a.remove();
  }
  _getOpenDataUrl(blobUrl, filename, dest = null) {
    let url = "?file=" + encodeURIComponent(blobUrl + "#" + filename);
    if (dest) {
      url += `#${escape(dest)}`;
    }
    return url;
  }
}

;// ./web/editor_undo_bar.js


class EditorUndoBar {
  #closeButton = null;
  #container;
  #eventBus = null;
  #focusTimeout = null;
  #initController = null;
  isOpen = false;
  #message;
  #showController = null;
  #undoButton;
  static #l10nMessages = Object.freeze({
    highlight: "pdfjs-editor-undo-bar-message-highlight",
    freetext: "pdfjs-editor-undo-bar-message-freetext",
    stamp: "pdfjs-editor-undo-bar-message-stamp",
    ink: "pdfjs-editor-undo-bar-message-ink",
    signature: "pdfjs-editor-undo-bar-message-signature",
    comment: "pdfjs-editor-undo-bar-message-comment",
    _multiple: "pdfjs-editor-undo-bar-message-multiple"
  });
  constructor({
    container,
    message,
    undoButton,
    closeButton
  }, eventBus) {
    this.#container = container;
    this.#message = message;
    this.#undoButton = undoButton;
    this.#closeButton = closeButton;
    this.#eventBus = eventBus;
  }
  destroy() {
    this.#initController?.abort();
    this.#initController = null;
    this.hide();
  }
  show(undoAction, messageData) {
    if (!this.#initController) {
      this.#initController = new AbortController();
      const domOpts = {
        signal: this.#initController.signal
      };
      const evtOpts = {
        signal: this.#initController.signal,
        ...internalOpt
      };
      const boundHide = this.hide.bind(this);
      this.#container.addEventListener("contextmenu", noContextMenu, domOpts);
      this.#closeButton.addEventListener("click", boundHide, domOpts);
      this.#eventBus.on("beforeprint", boundHide, evtOpts);
      this.#eventBus.on("download", boundHide, evtOpts);
    }
    this.hide();
    if (typeof messageData === "string") {
      this.#message.setAttribute("data-l10n-id", EditorUndoBar.#l10nMessages[messageData]);
    } else {
      this.#message.setAttribute("data-l10n-id", EditorUndoBar.#l10nMessages._multiple);
      this.#message.setAttribute("data-l10n-args", JSON.stringify({
        count: messageData
      }));
    }
    this.isOpen = true;
    this.#container.hidden = false;
    this.#showController = new AbortController();
    this.#undoButton.addEventListener("click", () => {
      undoAction();
      this.hide();
    }, {
      signal: this.#showController.signal
    });
    this.#focusTimeout = setTimeout(() => {
      if (!this.#container.contains(document.activeElement)) {
        this.#container.focus();
      }
      this.#focusTimeout = null;
    }, 100);
  }
  hide() {
    if (!this.isOpen) {
      return;
    }
    this.isOpen = false;
    this.#container.hidden = true;
    this.#showController?.abort();
    this.#showController = null;
    if (this.#focusTimeout) {
      clearTimeout(this.#focusTimeout);
      this.#focusTimeout = null;
    }
  }
}

;// ./web/overlay_manager.js
class OverlayManager {
  #overlays = new WeakMap();
  #active = null;
  get active() {
    return this.#active;
  }
  async register(dialog, canForceClose = false) {
    if (typeof dialog !== "object") {
      throw new Error("Not enough parameters.");
    } else if (this.#overlays.has(dialog)) {
      throw new Error("The overlay is already registered.");
    }
    this.#overlays.set(dialog, {
      canForceClose
    });
    dialog.addEventListener("cancel", ({
      target
    }) => {
      if (this.#active === target) {
        this.#active = null;
      }
    });
  }
  async open(dialog) {
    if (!this.#overlays.has(dialog)) {
      throw new Error("The overlay does not exist.");
    } else if (this.#active) {
      if (this.#active === dialog) {
        throw new Error("The overlay is already active.");
      } else if (this.#overlays.get(dialog).canForceClose) {
        await this.close();
      } else {
        throw new Error("Another overlay is currently active.");
      }
    }
    this.#active = dialog;
    dialog.showModal();
  }
  async close(dialog = this.#active) {
    if (!this.#overlays.has(dialog)) {
      throw new Error("The overlay does not exist.");
    } else if (!this.#active) {
      throw new Error("The overlay is currently not active.");
    } else if (this.#active !== dialog) {
      throw new Error("Another overlay is currently active.");
    }
    dialog.close();
    this.#active = null;
  }
  async closeIfActive(dialog) {
    if (this.#active === dialog) {
      await this.close(dialog);
    }
  }
}

;// ./web/password_prompt.js

class PasswordPrompt {
  #activeCapability = null;
  #updateCallback = null;
  #reason = null;
  constructor(options, overlayManager, isViewerEmbedded = false) {
    this.dialog = options.dialog;
    this.label = options.label;
    this.input = options.input;
    this.submitButton = options.submitButton;
    this.cancelButton = options.cancelButton;
    this.overlayManager = overlayManager;
    this._isViewerEmbedded = isViewerEmbedded;
    this.submitButton.addEventListener("click", this.#verify.bind(this));
    this.cancelButton.addEventListener("click", this.close.bind(this));
    this.input.addEventListener("keydown", e => {
      if (e.keyCode === 13) {
        this.#verify();
        e.preventDefault();
      }
    });
    this.overlayManager.register(this.dialog, true);
    this.dialog.addEventListener("close", this.#cancel.bind(this));
  }
  async open() {
    await this.#activeCapability?.promise;
    this.#activeCapability = Promise.withResolvers();
    try {
      await this.overlayManager.open(this.dialog);
    } catch (ex) {
      this.#activeCapability.resolve();
      throw ex;
    }
    const passwordIncorrect = this.#reason === PasswordResponses.INCORRECT_PASSWORD;
    if (!this._isViewerEmbedded || passwordIncorrect) {
      this.input.focus();
    }
    this.label.setAttribute("data-l10n-id", passwordIncorrect ? "pdfjs-password-invalid" : "pdfjs-password-label");
  }
  async close() {
    this.overlayManager.closeIfActive(this.dialog);
  }
  #verify() {
    const password = this.input.value;
    if (password?.length > 0) {
      this.#invokeCallback(password);
    }
  }
  #cancel() {
    this.#invokeCallback(new Error("PasswordPrompt cancelled."));
    this.#activeCapability.resolve();
  }
  #invokeCallback(password) {
    if (!this.#updateCallback) {
      return;
    }
    this.close();
    this.input.value = "";
    this.#updateCallback(password);
    this.#updateCallback = null;
  }
  async setUpdateCallback(updateCallback, reason) {
    if (this.#activeCapability) {
      await this.#activeCapability.promise;
    }
    this.#updateCallback = updateCallback;
    this.#reason = reason;
  }
}

;// ./web/base_tree_viewer.js


const TREEITEM_SELECTED_CLASS = "selected";
class BaseTreeViewer {
  constructor(options) {
    this.container = options.container;
    this.eventBus = options.eventBus;
    this._l10n = options.l10n;
    this.reset();
  }
  reset() {
    this._pdfDocument = null;
    this._lastToggleIsShow = true;
    this._currentTreeItem = null;
    this.container.replaceChildren();
    this.container.classList.remove("withNesting");
  }
  _dispatchEvent(count) {
    throw new Error("Not implemented: _dispatchEvent");
  }
  _bindLink(element, params) {
    throw new Error("Not implemented: _bindLink");
  }
  _normalizeTextContent(str) {
    return removeNullCharacters(str, true) || "\u2013";
  }
  _addToggleButton(div, hidden = false) {
    const toggler = document.createElement("div");
    toggler.className = "treeItemToggler";
    if (hidden) {
      toggler.classList.add("treeItemsHidden");
    }
    div.prepend(toggler);
  }
  _toggleTreeItem(root, show = false) {
    this._l10n.pause();
    this._lastToggleIsShow = show;
    for (const toggler of root.querySelectorAll(".treeItemToggler")) {
      toggler.classList.toggle("treeItemsHidden", !show);
    }
    this._l10n.resume();
  }
  _toggleAllTreeItems() {
    this._toggleTreeItem(this.container, !this._lastToggleIsShow);
  }
  _finishRendering(fragment, count, hasAnyNesting = false) {
    if (hasAnyNesting) {
      this.container.classList.add("withNesting");
      this._lastToggleIsShow = !fragment.querySelector(".treeItemsHidden");
      this.container.addEventListener("click", e => {
        const {
          target
        } = e;
        if (!target.classList.contains("treeItemToggler")) {
          return;
        }
        stopEvent(e);
        target.classList.toggle("treeItemsHidden");
        if (e.shiftKey) {
          const shouldShowAll = !target.classList.contains("treeItemsHidden");
          this._toggleTreeItem(target.parentNode, shouldShowAll);
        }
      });
    }
    this._l10n.pause();
    this.container.append(fragment);
    this._l10n.resume();
    this._dispatchEvent(count);
  }
  render(params) {
    throw new Error("Not implemented: render");
  }
  _updateCurrentTreeItem(treeItem = null) {
    if (this._currentTreeItem) {
      this._currentTreeItem.classList.remove(TREEITEM_SELECTED_CLASS);
      this._currentTreeItem = null;
    }
    if (treeItem) {
      treeItem.classList.add(TREEITEM_SELECTED_CLASS);
      this._currentTreeItem = treeItem;
    }
  }
  _scrollToCurrentTreeItem(treeItem) {
    if (!treeItem) {
      return;
    }
    this._l10n.pause();
    let currentNode = treeItem.parentNode;
    while (currentNode && currentNode !== this.container) {
      if (currentNode.classList.contains("treeItem")) {
        const toggler = currentNode.firstElementChild;
        toggler?.classList.remove("treeItemsHidden");
      }
      currentNode = currentNode.parentNode;
    }
    this._l10n.resume();
    this._updateCurrentTreeItem(treeItem);
    treeItem.scrollIntoView({
      behavior: "instant",
      block: "center",
      inline: "center",
      container: "nearest"
    });
  }
}

;// ./web/pdf_attachment_viewer.js



class PDFAttachmentViewer extends BaseTreeViewer {
  constructor(options) {
    super(options);
    this.downloadManager = options.downloadManager;
    this.linkService = options.linkService;
    this.eventBus.on("fileattachmentannotation", this.#appendAttachment.bind(this), internalOpt);
  }
  reset(keepRenderedCapability = false) {
    super.reset();
    this._attachments = null;
    if (!keepRenderedCapability) {
      this._renderedCapability = Promise.withResolvers();
    }
    this._pendingDispatchEvent = false;
  }
  async _dispatchEvent(attachmentsCount) {
    this._renderedCapability.resolve();
    if (attachmentsCount === 0 && !this._pendingDispatchEvent) {
      this._pendingDispatchEvent = true;
      await waitOnEventOrTimeout({
        target: this.eventBus,
        name: "annotationlayerrendered",
        delay: 1000
      });
      if (!this._pendingDispatchEvent) {
        return;
      }
    }
    this._pendingDispatchEvent = false;
    this.eventBus.dispatch("attachmentsloaded", {
      source: this,
      attachmentsCount
    });
  }
  _bindLink(element, {
    attachmentId,
    content: fallbackContent,
    description,
    filename
  }) {
    if (description) {
      element.title = description;
    }
    const openAttachment = async () => {
      const content = attachmentId ? await this.linkService.getAttachmentContent(attachmentId) : fallbackContent;
      if (content) {
        this.downloadManager?.openOrDownloadData(content, filename);
      }
    };
    element.onclick = () => {
      openAttachment();
      return false;
    };
  }
  render({
    attachments,
    keepRenderedCapability = false
  }) {
    if (this._attachments) {
      this.reset(keepRenderedCapability);
    }
    this._attachments = attachments || null;
    if (!attachments) {
      this._dispatchEvent(0);
      return;
    }
    const fragment = document.createDocumentFragment();
    const ul = document.createElement("ul");
    fragment.append(ul);
    let attachmentsCount = 0;
    for (const [name, item] of attachments) {
      const li = document.createElement("li");
      ul.append(li);
      const element = document.createElement("a");
      li.append(element);
      this._bindLink(element, {
        ...item,
        attachmentId: item.attachmentId ?? name
      });
      element.textContent = this._normalizeTextContent(item.filename);
      attachmentsCount++;
    }
    this._finishRendering(fragment, attachmentsCount);
  }
  #appendAttachment(item) {
    const renderedPromise = this._renderedCapability.promise;
    renderedPromise.then(() => {
      if (renderedPromise !== this._renderedCapability.promise) {
        return;
      }
      const attachments = new Map(this._attachments);
      if (attachments.has(item.filename)) {
        return;
      }
      attachments.set(item.filename, item);
      this.render({
        attachments,
        keepRenderedCapability: true
      });
    });
  }
}

;// ./web/grab_to_pan.js

const CSS_CLASS_GRAB = "grab-to-pan-grab";
class GrabToPan {
  #activateAC = null;
  #mouseDownAC = null;
  #scrollAC = null;
  constructor({
    element
  }) {
    this.element = element;
    this.document = element.ownerDocument;
    const overlay = this.overlay = document.createElement("div");
    overlay.className = "grab-to-pan-grabbing";
  }
  activate() {
    if (!this.#activateAC) {
      this.#activateAC = new AbortController();
      this.element.addEventListener("mousedown", this.#onMouseDown.bind(this), {
        capture: true,
        signal: this.#activateAC.signal
      });
      this.element.classList.add(CSS_CLASS_GRAB);
    }
  }
  deactivate() {
    if (this.#activateAC) {
      this.#activateAC.abort();
      this.#activateAC = null;
      this.#endPan();
      this.element.classList.remove(CSS_CLASS_GRAB);
    }
  }
  ignoreTarget(node) {
    return node.matches("a[href], a[href] *, input, textarea, button, button *, select, option");
  }
  #onMouseDown(event) {
    if (event.button !== 0 || this.ignoreTarget(event.target)) {
      return;
    }
    if (event.originalTarget) {
      try {
        event.originalTarget.tagName;
      } catch {
        return;
      }
    }
    this.scrollLeftStart = this.element.scrollLeft;
    this.scrollTopStart = this.element.scrollTop;
    this.clientXStart = event.clientX;
    this.clientYStart = event.clientY;
    this.#mouseDownAC = new AbortController();
    const boundEndPan = this.#endPan.bind(this),
      mouseOpts = {
        capture: true,
        signal: this.#mouseDownAC.signal
      };
    this.document.addEventListener("mousemove", this.#onMouseMove.bind(this), mouseOpts);
    this.document.addEventListener("mouseup", boundEndPan, mouseOpts);
    this.#scrollAC = new AbortController();
    this.element.addEventListener("scroll", boundEndPan, {
      capture: true,
      signal: this.#scrollAC.signal
    });
    stopEvent(event);
    const focusedElement = document.activeElement;
    if (focusedElement && !focusedElement.contains(event.target)) {
      focusedElement.blur();
    }
  }
  #onMouseMove(event) {
    this.#scrollAC?.abort();
    this.#scrollAC = null;
    if (!(event.buttons & 1)) {
      this.#endPan();
      return;
    }
    const xDiff = event.clientX - this.clientXStart;
    const yDiff = event.clientY - this.clientYStart;
    this.element.scrollTo({
      top: this.scrollTopStart - yDiff,
      left: this.scrollLeftStart - xDiff,
      behavior: "instant"
    });
    if (!this.overlay.parentNode) {
      document.body.append(this.overlay);
    }
  }
  #endPan() {
    this.#mouseDownAC?.abort();
    this.#mouseDownAC = null;
    this.#scrollAC?.abort();
    this.#scrollAC = null;
    this.overlay.remove();
  }
}

;// ./web/pdf_cursor_tools.js




class PDFCursorTools {
  #active = CursorTool.SELECT;
  #prevActive = null;
  constructor({
    container,
    eventBus,
    cursorToolOnLoad = CursorTool.SELECT
  }) {
    this.container = container;
    this.eventBus = eventBus;
    this.#addEventListeners();
    Promise.resolve().then(() => {
      this.switchTool(cursorToolOnLoad);
    });
  }
  get activeTool() {
    return this.#active;
  }
  switchTool(tool) {
    if (this.#prevActive !== null) {
      return;
    }
    this.#switchTool(tool);
  }
  #switchTool(tool, disabled = false) {
    if (tool === this.#active) {
      if (this.#prevActive !== null) {
        this.eventBus.dispatch("cursortoolchanged", {
          source: this,
          tool,
          disabled
        });
      }
      return;
    }
    const disableActiveTool = () => {
      switch (this.#active) {
        case CursorTool.SELECT:
          break;
        case CursorTool.HAND:
          this._handTool.deactivate();
          break;
        case CursorTool.ZOOM:
      }
    };
    switch (tool) {
      case CursorTool.SELECT:
        disableActiveTool();
        break;
      case CursorTool.HAND:
        disableActiveTool();
        this._handTool.activate();
        break;
      case CursorTool.ZOOM:
      default:
        console.error(`switchTool: "${tool}" is an unsupported value.`);
        return;
    }
    this.#active = tool;
    this.eventBus.dispatch("cursortoolchanged", {
      source: this,
      tool,
      disabled
    });
  }
  #addEventListeners() {
    const {
      eventBus
    } = this;
    eventBus.on("switchcursortool", evt => {
      if (!evt.reset) {
        this.switchTool(evt.tool);
      } else if (this.#prevActive !== null) {
        annotationEditorMode = AnnotationEditorType.NONE;
        presentationModeState = PresentationModeState.NORMAL;
        enableActive();
      }
    }, internalOpt);
    let annotationEditorMode = AnnotationEditorType.NONE,
      presentationModeState = PresentationModeState.NORMAL;
    const disableActive = () => {
      this.#prevActive ??= this.#active;
      this.#switchTool(CursorTool.SELECT, true);
    };
    const enableActive = () => {
      if (this.#prevActive !== null && annotationEditorMode === AnnotationEditorType.NONE && presentationModeState === PresentationModeState.NORMAL) {
        this.#switchTool(this.#prevActive);
        this.#prevActive = null;
      }
    };
    eventBus.on("annotationeditormodechanged", ({
      mode
    }) => {
      annotationEditorMode = mode;
      if (mode === AnnotationEditorType.NONE) {
        enableActive();
      } else {
        disableActive();
      }
    }, internalOpt);
    eventBus.on("presentationmodechanged", ({
      state
    }) => {
      presentationModeState = state;
      if (state === PresentationModeState.NORMAL) {
        enableActive();
      } else if (state === PresentationModeState.FULLSCREEN) {
        disableActive();
      }
    }, internalOpt);
  }
  get _handTool() {
    return shadow(this, "_handTool", new GrabToPan({
      element: this.container
    }));
  }
}

;// ./web/pdf_document_properties.js



const NON_METRIC_LOCALES = ["en-us", "en-lr", "my"];
const US_PAGE_NAMES = {
  "8.5x11": "pdfjs-document-properties-page-size-name-letter",
  "8.5x14": "pdfjs-document-properties-page-size-name-legal"
};
const METRIC_PAGE_NAMES = {
  "297x420": "pdfjs-document-properties-page-size-name-a-three",
  "210x297": "pdfjs-document-properties-page-size-name-a-four"
};
function getPageName(size, isPortrait, pageNames) {
  const width = isPortrait ? size.width : size.height;
  const height = isPortrait ? size.height : size.width;
  return pageNames[`${width}x${height}`];
}
class PDFDocumentProperties {
  #fieldData = null;
  constructor({
    dialog,
    fields,
    closeButton
  }, overlayManager, eventBus, l10n, fileNameLookup, titleLookup) {
    this.dialog = dialog;
    this.fields = fields;
    this.overlayManager = overlayManager;
    this.l10n = l10n;
    this._fileNameLookup = fileNameLookup;
    this._titleLookup = titleLookup;
    this.#reset();
    closeButton.addEventListener("click", this.close.bind(this));
    this.overlayManager.register(this.dialog);
    eventBus.on("pagechanging", evt => {
      this._currentPageNumber = evt.pageNumber;
    }, internalOpt);
    eventBus.on("rotationchanging", evt => {
      this._pagesRotation = evt.pagesRotation;
    }, internalOpt);
  }
  async open() {
    await Promise.all([this.overlayManager.open(this.dialog), this._dataAvailableCapability.promise]);
    const currentPageNumber = this._currentPageNumber;
    const pagesRotation = this._pagesRotation;
    if (this.#fieldData && currentPageNumber === this.#fieldData._currentPageNumber && pagesRotation === this.#fieldData._pagesRotation) {
      this.#updateUI();
      return;
    }
    const [{
      info,
      metadata,
      contentLength
    }, pageSize] = await Promise.all([this.pdfDocument.getMetadata(), this.pdfDocument.getPage(currentPageNumber).then(pdfPage => this.#parsePageSize(pdfPage, pagesRotation), reason => {
      console.error(`PDFDocumentProperties - unable to get page ${currentPageNumber}.`, reason);
      return undefined;
    })]);
    this.#fieldData = Object.freeze({
      fileName: this._fileNameLookup(),
      fileSize: this.#parseFileSize(contentLength),
      title: this._titleLookup(),
      author: metadata?.get("dc:creator")?.join("\n") || info.Author,
      subject: metadata?.get("dc:subject")?.join("\n") || info.Subject,
      keywords: metadata?.get("pdf:keywords") || info.Keywords,
      creationDate: this.#parseDate(metadata?.get("xmp:createdate"), info.CreationDate),
      modificationDate: this.#parseDate(metadata?.get("xmp:modifydate"), info.ModDate),
      creator: metadata?.get("xmp:creatortool") || info.Creator,
      producer: metadata?.get("pdf:producer") || info.Producer,
      version: info.PDFFormatVersion,
      pageCount: this.pdfDocument.numPages,
      pageSize,
      linearized: this.#parseLinearization(info.IsLinearized),
      _currentPageNumber: currentPageNumber,
      _pagesRotation: pagesRotation
    });
    this.#updateUI();
    const {
      length
    } = await this.pdfDocument.getDownloadInfo();
    if (contentLength === length) {
      return;
    }
    const data = Object.assign(Object.create(null), this.#fieldData);
    data.fileSize = this.#parseFileSize(length);
    this.#fieldData = Object.freeze(data);
    this.#updateUI();
  }
  async close() {
    this.overlayManager.close(this.dialog);
  }
  setDocument(pdfDocument) {
    if (this.pdfDocument) {
      this.#reset();
      this.#updateUI();
    }
    if (!pdfDocument) {
      return;
    }
    this.pdfDocument = pdfDocument;
    this._dataAvailableCapability.resolve();
  }
  #reset() {
    this.pdfDocument = null;
    this.#fieldData = null;
    this._dataAvailableCapability = Promise.withResolvers();
    this._currentPageNumber = 1;
    this._pagesRotation = 0;
  }
  #updateUI() {
    if (this.#fieldData && this.overlayManager.active !== this.dialog) {
      return;
    }
    for (const id in this.fields) {
      const field = this.fields[id],
        data = this.#fieldData?.[id];
      if (data?.id) {
        field.setAttribute("data-l10n-id", data.id);
        if (data.args) {
          field.setAttribute("data-l10n-args", JSON.stringify(data.args));
        }
      } else {
        field.removeAttribute("data-l10n-id");
        field.removeAttribute("data-l10n-args");
        field.textContent = data || data === 0 ? data : "-";
      }
    }
  }
  #parseFileSize(b = 0) {
    const kb = b / 1024,
      mb = kb / 1024;
    return kb ? {
      id: mb >= 1 ? "pdfjs-document-properties-size-mb" : "pdfjs-document-properties-size-kb",
      args: {
        mb,
        kb,
        b
      }
    } : undefined;
  }
  async #parsePageSize(pdfPage, pagesRotation) {
    let pageSizeInches = getPageSizeInches(pdfPage);
    if (pagesRotation % 180 !== 0) {
      pageSizeInches = {
        width: pageSizeInches.height,
        height: pageSizeInches.width
      };
    }
    const isPortrait = isPortraitOrientation(pageSizeInches),
      nonMetric = NON_METRIC_LOCALES.includes(this.l10n.getLanguage());
    let sizeInches = {
      width: Math.round(pageSizeInches.width * 100) / 100,
      height: Math.round(pageSizeInches.height * 100) / 100
    };
    let sizeMillimeters = {
      width: Math.round(pageSizeInches.width * 25.4 * 10) / 10,
      height: Math.round(pageSizeInches.height * 25.4 * 10) / 10
    };
    let nameId = getPageName(sizeInches, isPortrait, US_PAGE_NAMES) || getPageName(sizeMillimeters, isPortrait, METRIC_PAGE_NAMES);
    if (!nameId && !(Number.isInteger(sizeMillimeters.width) && Number.isInteger(sizeMillimeters.height))) {
      const exactMillimeters = {
        width: pageSizeInches.width * 25.4,
        height: pageSizeInches.height * 25.4
      };
      const intMillimeters = {
        width: Math.round(sizeMillimeters.width),
        height: Math.round(sizeMillimeters.height)
      };
      if (Math.abs(exactMillimeters.width - intMillimeters.width) < 0.1 && Math.abs(exactMillimeters.height - intMillimeters.height) < 0.1) {
        nameId = getPageName(intMillimeters, isPortrait, METRIC_PAGE_NAMES);
        if (nameId) {
          sizeInches = {
            width: Math.round(intMillimeters.width / 25.4 * 100) / 100,
            height: Math.round(intMillimeters.height / 25.4 * 100) / 100
          };
          sizeMillimeters = intMillimeters;
        }
      }
    }
    const {
      width,
      height
    } = nonMetric ? sizeInches : sizeMillimeters;
    const ids = [nonMetric ? "pdfjs-document-properties-page-size-unit-inches" : "pdfjs-document-properties-page-size-unit-millimeters", isPortrait ? "pdfjs-document-properties-page-size-orientation-portrait" : "pdfjs-document-properties-page-size-orientation-landscape"];
    if (nameId) {
      ids.push(nameId);
    }
    const [unit, orientation, name] = await this.l10n.get(ids);
    return {
      id: name ? "pdfjs-document-properties-page-size-dimension-name-string" : "pdfjs-document-properties-page-size-dimension-string",
      args: {
        width,
        height,
        unit,
        name,
        orientation
      }
    };
  }
  #parseDate(metadataDate, infoDate) {
    const dateObj = Date.parse(metadataDate) || PDFDateString.toDateObject(infoDate);
    return dateObj ? {
      id: "pdfjs-document-properties-date-time-string",
      args: {
        dateObj: dateObj.valueOf()
      }
    } : undefined;
  }
  #parseLinearization(isLinearized) {
    return {
      id: isLinearized ? "pdfjs-document-properties-linearized-yes" : "pdfjs-document-properties-linearized-no"
    };
  }
}

;// ./web/pdf_find_utils.js

let wordSegmenter = null;
let graphemeSegmenter = null;
function isWordBreakAt(content, pos) {
  graphemeSegmenter ||= new Intl.Segmenter(undefined, {
    granularity: "grapheme"
  });
  const graphemes = graphemeSegmenter.segment(content);
  const after = graphemes.containing(pos);
  if (after.index !== pos) {
    return false;
  }
  wordSegmenter ||= new Intl.Segmenter(undefined, {
    granularity: "word"
  });
  const before = graphemes.containing(pos - 1).segment;
  return wordSegmenter.segment(before + after.segment).containing(before.length).index === before.length;
}
function isEntireWord(content, startIdx, length) {
  const endIdx = startIdx + length;
  return (startIdx === 0 || isWordBreakAt(content, startIdx)) && (endIdx === content.length || isWordBreakAt(content, endIdx));
}
let NormalizeWithNFKC;
function getNormalizeWithNFKC() {
  if (!NormalizeWithNFKC) {
    const ranges = [];
    const range = [];
    const flushRange = () => {
      if (range.length !== 2) {
        return;
      }
      const [start, end] = range;
      const first = String.fromCharCode(start);
      ranges.push(start === end ? first : `${first}-${String.fromCharCode(end)}`);
    };
    const diacriticsRegex = /^\p{M}$/u;
    for (let i = 0; i < 65536; i++) {
      if (i >= 0xd800 && i <= 0xdfff) {
        continue;
      }
      const c = String.fromCharCode(i);
      if (c.normalize("NFKC") !== c && !diacriticsRegex.test(c)) {
        if (range.length === 2 && range[1] + 1 === i) {
          range[1] = i;
        } else {
          flushRange();
          range[0] = range[1] = i;
        }
      }
    }
    flushRange();
    const rangesStr = ranges.join("");
    if (!NormalizeWithNFKC) {
      NormalizeWithNFKC = rangesStr;
    } else if (rangesStr !== NormalizeWithNFKC) {
      for (let i = 1; i < rangesStr.length; i++) {
        if (rangesStr[i] !== NormalizeWithNFKC[i]) {
          console.log(`Difference at index ${i}: ` + `U+${rangesStr.charCodeAt(i).toString(16).toUpperCase().padStart(4, "0")}` + `!== U+${NormalizeWithNFKC.charCodeAt(i).toString(16).toUpperCase().padStart(4, "0")}`);
          break;
        }
      }
      throw new Error("getNormalizeWithNFKC - update the `NormalizeWithNFKC` string.");
    }
  }
  return NormalizeWithNFKC;
}

;// ./web/pdf_find_controller.js



const FindState = {
  FOUND: 0,
  NOT_FOUND: 1,
  WRAPPED: 2,
  PENDING: 3
};
const CHARACTERS_TO_NORMALIZE = new Map([["\u2010", "-"], ["\u2018", "'"], ["\u2019", "'"], ["\u201A", "'"], ["\u201B", "'"], ["\u201C", '"'], ["\u201D", '"'], ["\u201E", '"'], ["\u201F", '"'], ["\u00BC", "1/4"], ["\u00BD", "1/2"], ["\u00BE", "3/4"]]);
const DIACRITICS_EXCEPTION = new Set([0x3099, 0x309a, 0x094d, 0x09cd, 0x0a4d, 0x0acd, 0x0b4d, 0x0bcd, 0x0c4d, 0x0ccd, 0x0d3b, 0x0d3c, 0x0d4d, 0x0dca, 0x0e3a, 0x0eba, 0x0f84, 0x1039, 0x103a, 0x1714, 0x1734, 0x17d2, 0x1a60, 0x1b44, 0x1baa, 0x1bab, 0x1bf2, 0x1bf3, 0x2d7f, 0xa806, 0xa82c, 0xa8c4, 0xa953, 0xa9c0, 0xaaf6, 0xabed, 0x0c56, 0x0f71, 0x0f72, 0x0f7a, 0x0f7b, 0x0f7c, 0x0f7d, 0x0f80, 0x0f74]);
let DIACRITICS_EXCEPTION_STR;
const DIACRITICS_REG_EXP = /\p{M}+/gu;
const SPECIAL_CHARS_REG_EXP = /([+^$|])|(\p{P}+)|(\s+)|(\p{M})|(\p{L})/gu;
const SYLLABLES_REG_EXP = /[\uAC00-\uD7AF\uFA6C\uFACF-\uFAD1\uFAD5-\uFAD7]+/g;
const SYLLABLES_LENGTHS = new Map();
const FIRST_CHAR_SYLLABLES_REG_EXP = "[\\u1100-\\u1112\\ud7a4-\\ud7af\\ud84a\\ud84c\\ud850\\ud854\\ud857\\ud85f]";
const NFKC_CHARS_TO_NORMALIZE = new Map();
let noSyllablesRegExp = null;
let withSyllablesRegExp = null;
function normalize(text, options = {}) {
  const syllablePositions = [];
  let m;
  while ((m = SYLLABLES_REG_EXP.exec(text)) !== null) {
    let {
      index
    } = m;
    for (const char of m[0]) {
      let len = SYLLABLES_LENGTHS.get(char);
      if (!len) {
        len = char.normalize("NFD").length;
        SYLLABLES_LENGTHS.set(char, len);
      }
      syllablePositions.push([len, index++]);
    }
  }
  const hasSyllables = syllablePositions.length > 0;
  const ignoreDashEOL = options.ignoreDashEOL ?? false;
  let normalizationRegex;
  if (!hasSyllables && noSyllablesRegExp) {
    normalizationRegex = noSyllablesRegExp;
  } else if (hasSyllables && withSyllablesRegExp) {
    normalizationRegex = withSyllablesRegExp;
  } else {
    const replace = CHARACTERS_TO_NORMALIZE.keys().join("");
    const toNormalizeWithNFKC = getNormalizeWithNFKC();
    const CJK = "(?:\\p{Ideographic}|[\u3040-\u30FF])";
    const HKDiacritics = "(?:\u3099|\u309A)";
    const BrokenWord = `\\p{Ll}-\\n(?=\\p{Ll})|\\p{Lu}-\\n(?=\\p{L})`;
    const regexps = [`[${replace}]`, `[${toNormalizeWithNFKC}]`, `${HKDiacritics}\\n`, "\\p{M}+(?:-\\n)?", `${BrokenWord}`, "\\S-\\n", `${CJK}\\n`, "\\n", hasSyllables ? FIRST_CHAR_SYLLABLES_REG_EXP : "\\u0000"];
    normalizationRegex = new RegExp(regexps.map(r => `(${r})`).join("|"), "gmu");
    if (hasSyllables) {
      withSyllablesRegExp = normalizationRegex;
    } else {
      noSyllablesRegExp = normalizationRegex;
    }
  }
  const rawDiacriticsPositions = [];
  while ((m = DIACRITICS_REG_EXP.exec(text)) !== null) {
    rawDiacriticsPositions.push([m[0].length, m.index]);
  }
  let normalized = text.normalize("NFD");
  const positions = [0, 0];
  let rawDiacriticsIndex = 0;
  let syllableIndex = 0;
  let shift = 0;
  let shiftOrigin = 0;
  let eol = 0;
  let hasDiacritics = false;
  normalized = normalized.replace(normalizationRegex, (match, p1, p2, p3, p4, p5, p6, p7, p8, p9, i) => {
    i -= shiftOrigin;
    if (p1) {
      const replacement = CHARACTERS_TO_NORMALIZE.get(p1);
      const jj = replacement.length;
      for (let j = 1; j < jj; j++) {
        positions.push(i - shift + j, shift - j);
      }
      shift -= jj - 1;
      return replacement;
    }
    if (p2) {
      const replacement = NFKC_CHARS_TO_NORMALIZE.getOrInsertComputed(p2, () => p2.normalize("NFKC"));
      const jj = replacement.length;
      for (let j = 1; j < jj; j++) {
        positions.push(i - shift + j, shift - j);
      }
      shift -= jj - 1;
      return replacement;
    }
    if (p3) {
      hasDiacritics = true;
      if (i + eol === rawDiacriticsPositions[rawDiacriticsIndex]?.[1]) {
        ++rawDiacriticsIndex;
      } else {
        positions.push(i - 1 - shift + 1, shift - 1);
        shift -= 1;
        shiftOrigin += 1;
      }
      positions.push(i - shift + 1, shift);
      shiftOrigin += 1;
      eol += 1;
      return p3.charAt(0);
    }
    if (p4) {
      const hasTrailingDashEOL = p4.endsWith("\n");
      const len = hasTrailingDashEOL ? p4.length - 2 : p4.length;
      hasDiacritics = true;
      let jj = len;
      if (i + eol === rawDiacriticsPositions[rawDiacriticsIndex]?.[1]) {
        jj -= rawDiacriticsPositions[rawDiacriticsIndex][0];
        ++rawDiacriticsIndex;
      }
      for (let j = 1; j <= jj; j++) {
        positions.push(i - 1 - shift + j, shift - j);
      }
      shift -= jj;
      shiftOrigin += jj;
      if (hasTrailingDashEOL) {
        i += len - 1;
        positions.push(i - shift + 1, 1 + shift);
        shift += 1;
        shiftOrigin += 1;
        eol += 1;
        return p4.slice(0, len);
      }
      return p4;
    }
    if (p5) {
      if (ignoreDashEOL) {
        shiftOrigin += 1;
        eol += 1;
        return p5.slice(0, -1);
      }
      const len = p5.length - 2;
      positions.push(i - shift + len, 1 + shift);
      shift += 1;
      shiftOrigin += 1;
      eol += 1;
      return p5.slice(0, -2);
    }
    if (p6) {
      shiftOrigin += 1;
      eol += 1;
      return p6.slice(0, -1);
    }
    if (p7) {
      const len = p7.length - 1;
      positions.push(i - shift + len, shift);
      shiftOrigin += 1;
      eol += 1;
      return p7.slice(0, -1);
    }
    if (p8) {
      positions.push(i - shift + 1, shift - 1);
      shift -= 1;
      shiftOrigin += 1;
      eol += 1;
      return " ";
    }
    if (i + eol === syllablePositions[syllableIndex]?.[1]) {
      const newCharLen = syllablePositions[syllableIndex][0] - 1;
      ++syllableIndex;
      for (let j = 1; j <= newCharLen; j++) {
        positions.push(i - (shift - j), shift - j);
      }
      shift -= newCharLen;
      shiftOrigin += newCharLen;
    }
    return p9;
  });
  positions.push(normalized.length, shift);
  const starts = new Uint32Array(positions.length >> 1);
  const shifts = new Int32Array(positions.length >> 1);
  for (let i = 0, ii = positions.length; i < ii; i += 2) {
    starts[i >> 1] = positions[i];
    shifts[i >> 1] = positions[i + 1];
  }
  return [normalized, [starts, shifts], hasDiacritics];
}
function getOriginalIndex(diffs, pos, len) {
  if (!diffs) {
    return [pos, len];
  }
  const [starts, shifts] = diffs;
  const start = pos;
  const end = pos + len - 1;
  let i = binarySearchFirstItem(starts, x => x >= start);
  if (starts[i] > start) {
    --i;
  }
  let j = binarySearchFirstItem(starts, x => x >= end, i);
  if (starts[j] > end) {
    --j;
  }
  const oldStart = start + shifts[i];
  const oldEnd = end + shifts[j];
  const oldLen = oldEnd + 1 - oldStart;
  return [oldStart, oldLen];
}
class PDFFindController {
  #state = null;
  #updateMatchesCountOnProgress = true;
  #delay = 0;
  #visitedPagesCount = 0;
  #copiedPageData = null;
  #savedPageData = null;
  constructor({
    linkService,
    eventBus,
    delay = 250,
    updateMatchesCountOnProgress = true
  }) {
    this._linkService = linkService;
    this._eventBus = eventBus;
    this.#updateMatchesCountOnProgress = updateMatchesCountOnProgress;
    this.#delay = delay;
    this.onIsPageVisible = null;
    this.#reset();
    eventBus.on("find", this.#onFind.bind(this), internalOpt);
    eventBus.on("findbarclose", this.#onFindBarClose.bind(this), internalOpt);
    eventBus.on("pagesedited", this.#onPagesEdited.bind(this), internalOpt);
  }
  get highlightMatches() {
    return this._highlightMatches;
  }
  get pageMatches() {
    return this._pageMatches;
  }
  get pageMatchesLength() {
    return this._pageMatchesLength;
  }
  get selected() {
    return this._selected;
  }
  get state() {
    return this.#state;
  }
  setDocument(pdfDocument) {
    if (this._pdfDocument) {
      this.#reset();
    }
    if (!pdfDocument) {
      return;
    }
    this._pdfDocument = pdfDocument;
    this._firstPageCapability.resolve();
  }
  #onFind(state) {
    if (!state) {
      return;
    }
    const pdfDocument = this._pdfDocument;
    const {
      type
    } = state;
    if (this.#state === null || this.#shouldDirtyMatch(state)) {
      this._dirtyMatch = true;
    }
    this.#state = state;
    if (type !== "highlightallchange") {
      this.#updateUIState(FindState.PENDING);
    }
    this._firstPageCapability.promise.then(() => {
      if (!this._pdfDocument || pdfDocument && this._pdfDocument !== pdfDocument) {
        return;
      }
      this.#extractText();
      const findbarClosed = !this._highlightMatches;
      const pendingTimeout = !!this._findTimeout;
      if (this._findTimeout) {
        clearTimeout(this._findTimeout);
        this._findTimeout = null;
      }
      if (!type) {
        this._findTimeout = setTimeout(() => {
          this.#nextMatch();
          this._findTimeout = null;
        }, this.#delay);
      } else if (this._dirtyMatch) {
        this.#nextMatch();
      } else if (type === "again") {
        this.#nextMatch();
        if (findbarClosed && this.#state.highlightAll) {
          this.#updateAllPages();
        }
      } else if (type === "highlightallchange") {
        if (pendingTimeout) {
          this.#nextMatch();
        } else {
          this._highlightMatches = true;
        }
        this.#updateAllPages();
      } else {
        this.#nextMatch();
      }
    });
  }
  scrollMatchIntoView({
    element = null,
    pageIndex = -1,
    matchIndex = -1
  }) {
    if (!this._scrollMatches || !element) {
      return;
    } else if (matchIndex === -1 || matchIndex !== this._selected.matchIdx) {
      return;
    } else if (pageIndex === -1 || pageIndex !== this._selected.pageIdx) {
      return;
    }
    this._scrollMatches = false;
    element.scrollIntoView({
      block: "start",
      inline: "center"
    });
  }
  #reset() {
    this._highlightMatches = false;
    this._scrollMatches = false;
    this._pdfDocument = null;
    this._pageMatches = [];
    this._pageMatchesLength = [];
    this.#visitedPagesCount = 0;
    this.#state = null;
    this._selected = {
      pageIdx: -1,
      matchIdx: -1
    };
    this._offset = {
      pageIdx: null,
      matchIdx: null,
      wrapped: false
    };
    this._extractTextPromises = [];
    this._pageContents = [];
    this._pageDiffs = [];
    this._hasDiacritics = [];
    this._matchesCountTotal = 0;
    this._pagesToSearch = null;
    this._pendingFindMatches = new Set();
    this._resumePageIdx = null;
    this._dirtyMatch = false;
    clearTimeout(this._findTimeout);
    this._findTimeout = null;
    this.#copiedPageData = null;
    this._firstPageCapability = Promise.withResolvers();
  }
  get #query() {
    const {
      query
    } = this.#state;
    if (typeof query === "string") {
      if (query !== this._rawQuery) {
        this._rawQuery = query;
        [this._normalizedQuery] = normalize(query);
      }
      return this._normalizedQuery;
    }
    return (query || []).filter(Boolean).map(q => normalize(q)[0]);
  }
  #shouldDirtyMatch(state) {
    const newQuery = state.query,
      prevQuery = this.#state.query;
    const newType = typeof newQuery,
      prevType = typeof prevQuery;
    if (newType !== prevType) {
      return true;
    }
    if (newType === "string") {
      if (newQuery !== prevQuery) {
        return true;
      }
    } else if (JSON.stringify(newQuery) !== JSON.stringify(prevQuery)) {
      return true;
    }
    switch (state.type) {
      case "again":
        const pageNumber = this._selected.pageIdx + 1;
        const linkService = this._linkService;
        return pageNumber >= 1 && pageNumber <= linkService.pagesCount && pageNumber !== linkService.page && !(this.onIsPageVisible?.(pageNumber) ?? true);
      case "highlightallchange":
        return false;
    }
    return true;
  }
  #convertToRegExpString(query, hasDiacritics) {
    const {
      matchDiacritics
    } = this.#state;
    let isUnicode = false;
    const addExtraWhitespaces = (original, fixed) => {
      if (original === query) {
        return fixed;
      }
      if (query.startsWith(original)) {
        return `${fixed}[ ]*`;
      }
      return query.endsWith(original) ? `[ ]*${fixed}` : `[ ]*${fixed}[ ]*`;
    };
    query = query.replaceAll(SPECIAL_CHARS_REG_EXP, (match, p1, p2, p3, p4, p5) => {
      if (p1) {
        return addExtraWhitespaces(p1, RegExp.escape(p1));
      }
      if (p2) {
        return addExtraWhitespaces(p2, RegExp.escape(p2));
      }
      if (p3) {
        return "[ ]+";
      }
      if (matchDiacritics) {
        return p4 || p5;
      }
      if (p4) {
        return DIACRITICS_EXCEPTION.has(p4.charCodeAt(0)) ? p4 : "";
      }
      if (hasDiacritics) {
        isUnicode = true;
        return `${p5}\\p{M}*`;
      }
      return p5;
    });
    if (!query) {
      return [false, ""];
    }
    const trailingSpaces = "[ ]*";
    if (query.endsWith(trailingSpaces)) {
      query = query.slice(0, query.length - trailingSpaces.length);
    }
    query = query.replaceAll(/(?:\[ \][*+]){2,}/g, spaces => `[ ]{${spaces.split("+").length - 1},}`);
    if (query.startsWith("[ ]")) {
      query = `(?:(?<![ ])|(?![ ]{2}))${query}`;
    }
    if (matchDiacritics) {
      if (hasDiacritics) {
        DIACRITICS_EXCEPTION_STR ||= String.fromCharCode(...DIACRITICS_EXCEPTION);
        isUnicode = true;
        query = `${query}(?=[${DIACRITICS_EXCEPTION_STR}]|[^\\p{M}]|$)`;
      }
    }
    return [isUnicode, query];
  }
  #calculateMatch(pageIndex) {
    if (!this.#state) {
      return;
    }
    const query = this.#query;
    if (query.length === 0) {
      return;
    }
    const pageContent = this._pageContents[pageIndex];
    const matcherResult = this.match(query, pageContent, pageIndex);
    const matches = this._pageMatches[pageIndex] = [];
    const matchesLength = this._pageMatchesLength[pageIndex] = [];
    const diffs = this._pageDiffs[pageIndex];
    matcherResult?.forEach(({
      index,
      length
    }) => {
      const [matchPos, matchLen] = getOriginalIndex(diffs, index, length);
      if (matchLen) {
        matches.push(matchPos);
        matchesLength.push(matchLen);
      }
    });
    if (this.#state.highlightAll) {
      this.#updatePage(pageIndex);
    }
    if (this._resumePageIdx === pageIndex) {
      this._resumePageIdx = null;
      this.#nextPageMatch();
    }
    const pageMatchesCount = matches.length;
    this._matchesCountTotal += pageMatchesCount;
    if (this.#updateMatchesCountOnProgress) {
      if (pageMatchesCount > 0) {
        this.#updateUIResultsCount();
      }
    } else if (++this.#visitedPagesCount === this._linkService.pagesCount) {
      this.#updateUIResultsCount();
    }
  }
  match(query, pageContent, pageIndex) {
    const hasDiacritics = this._hasDiacritics[pageIndex];
    let isUnicode = false;
    if (typeof query === "string") {
      [isUnicode, query] = this.#convertToRegExpString(query, hasDiacritics);
    } else {
      query = query.sort().reverse().map(q => {
        const [isUnicodePart, queryPart] = this.#convertToRegExpString(q, hasDiacritics);
        isUnicode ||= isUnicodePart;
        return queryPart && `(${queryPart})`;
      }).filter(Boolean).join("|");
    }
    if (!query) {
      return undefined;
    }
    const {
      caseSensitive,
      entireWord
    } = this.#state;
    const flags = `g${isUnicode ? "u" : ""}${caseSensitive ? "" : "i"}`;
    query = new RegExp(query, flags);
    const matches = [];
    let match;
    while ((match = query.exec(pageContent)) !== null) {
      if (entireWord && !isEntireWord(pageContent, match.index, match[0].length)) {
        continue;
      }
      matches.push({
        index: match.index,
        length: match[0].length
      });
    }
    return matches;
  }
  #extractText() {
    if (this._extractTextPromises.length > 0) {
      return;
    }
    let deferred = Promise.resolve();
    const textOptions = {
      disableNormalization: true
    };
    const pdfDoc = this._pdfDocument;
    for (let i = 0, ii = this._linkService.pagesCount; i < ii; i++) {
      const {
        promise,
        resolve
      } = Promise.withResolvers();
      this._extractTextPromises[i] = promise;
      deferred = deferred.then(async () => {
        if (pdfDoc !== this._pdfDocument) {
          resolve();
          return;
        }
        try {
          const pdfPage = await pdfDoc.getPage(i + 1);
          const textContent = await pdfPage.getTextContent(textOptions);
          if (pdfDoc !== this._pdfDocument) {
            resolve();
            return;
          }
          const strBuf = [];
          for (const textItem of textContent.items) {
            strBuf.push(textItem.str);
            if (textItem.hasEOL) {
              strBuf.push("\n");
            }
          }
          [this._pageContents[i], this._pageDiffs[i], this._hasDiacritics[i]] = normalize(strBuf.join(""));
        } catch (ex) {
          if (pdfDoc !== this._pdfDocument) {
            resolve();
            return;
          }
          console.error(`Unable to get text content for page ${i + 1}`, ex);
          [this._pageContents[i], this._pageDiffs[i], this._hasDiacritics[i]] = ["", null, false];
        }
        resolve();
      });
    }
  }
  #updatePage(index) {
    if (this._scrollMatches && this._selected.pageIdx === index) {
      this._linkService.page = index + 1;
    }
    this._eventBus.dispatch("updatetextlayermatches", {
      source: this,
      pageIndex: index
    });
  }
  #updateAllPages() {
    this._eventBus.dispatch("updatetextlayermatches", {
      source: this,
      pageIndex: -1
    });
  }
  #nextMatch() {
    const previous = this.#state.findPrevious;
    const currentPageIndex = this._linkService.page - 1;
    const numPages = this._linkService.pagesCount;
    this._highlightMatches = true;
    if (this._dirtyMatch) {
      this._dirtyMatch = false;
      this._selected.pageIdx = this._selected.matchIdx = -1;
      this._offset.pageIdx = currentPageIndex;
      this._offset.matchIdx = null;
      this._offset.wrapped = false;
      this._resumePageIdx = null;
      this._pageMatches.length = 0;
      this._pageMatchesLength.length = 0;
      this.#visitedPagesCount = 0;
      this._matchesCountTotal = 0;
      this.#updateAllPages();
      for (let i = 0; i < numPages; i++) {
        if (this._pendingFindMatches.has(i)) {
          continue;
        }
        this._pendingFindMatches.add(i);
        this._extractTextPromises[i].then(() => {
          this._pendingFindMatches.delete(i);
          this.#calculateMatch(i);
        });
      }
    }
    const query = this.#query;
    if (query.length === 0) {
      this.#updateUIState(FindState.FOUND);
      return;
    }
    if (this._resumePageIdx) {
      return;
    }
    const offset = this._offset;
    this._pagesToSearch = numPages;
    if (offset.matchIdx !== null) {
      const numPageMatches = this._pageMatches[offset.pageIdx].length;
      if (!previous && offset.matchIdx + 1 < numPageMatches || previous && offset.matchIdx > 0) {
        offset.matchIdx = previous ? offset.matchIdx - 1 : offset.matchIdx + 1;
        this.#updateMatch(true);
        return;
      }
      this.#advanceOffsetPage(previous);
    }
    this.#nextPageMatch();
  }
  #matchesReady(matches) {
    const offset = this._offset;
    const numMatches = matches.length;
    const previous = this.#state.findPrevious;
    if (numMatches) {
      offset.matchIdx = previous ? numMatches - 1 : 0;
      this.#updateMatch(true);
      return true;
    }
    this.#advanceOffsetPage(previous);
    if (offset.wrapped) {
      offset.matchIdx = null;
      if (this._pagesToSearch < 0) {
        this.#updateMatch(false);
        return true;
      }
    }
    return false;
  }
  #nextPageMatch() {
    if (this._resumePageIdx !== null) {
      console.error("There can only be one pending page.");
    }
    let matches = null;
    do {
      const pageIdx = this._offset.pageIdx;
      matches = this._pageMatches[pageIdx];
      if (!matches) {
        this._resumePageIdx = pageIdx;
        break;
      }
    } while (!this.#matchesReady(matches));
  }
  #advanceOffsetPage(previous) {
    const offset = this._offset;
    const numPages = this._linkService.pagesCount;
    offset.pageIdx = previous ? offset.pageIdx - 1 : offset.pageIdx + 1;
    offset.matchIdx = null;
    this._pagesToSearch--;
    if (offset.pageIdx >= numPages || offset.pageIdx < 0) {
      offset.pageIdx = previous ? numPages - 1 : 0;
      offset.wrapped = true;
    }
  }
  #updateMatch(found = false) {
    let state = FindState.NOT_FOUND;
    const wrapped = this._offset.wrapped;
    this._offset.wrapped = false;
    if (found) {
      const previousPage = this._selected.pageIdx;
      this._selected.pageIdx = this._offset.pageIdx;
      this._selected.matchIdx = this._offset.matchIdx;
      state = wrapped ? FindState.WRAPPED : FindState.FOUND;
      if (previousPage !== -1 && previousPage !== this._selected.pageIdx) {
        this.#updatePage(previousPage);
      }
    }
    this.#updateUIState(state, this.#state.findPrevious);
    if (this._selected.pageIdx !== -1) {
      this._scrollMatches = true;
      this.#updatePage(this._selected.pageIdx);
    }
  }
  #onPagesEdited({
    pagesMapper,
    type,
    pageNumbers
  }) {
    if (this._extractTextPromises.length === 0) {
      return;
    }
    if (type === "copy") {
      const promises = new Map();
      const contents = new Map();
      const diffs = new Map();
      const diacritics = new Map();
      for (const pageNum of pageNumbers) {
        promises.set(pageNum, this._extractTextPromises[pageNum - 1]);
        contents.set(pageNum, this._pageContents[pageNum - 1]);
        diffs.set(pageNum, this._pageDiffs[pageNum - 1]);
        diacritics.set(pageNum, this._hasDiacritics[pageNum - 1]);
      }
      this.#copiedPageData = {
        promises,
        contents,
        diffs,
        diacritics
      };
      return;
    }
    if (type === "cancelCopy") {
      this.#copiedPageData = null;
      return;
    }
    if (type === "delete") {
      this.#savedPageData = {
        promises: this._extractTextPromises,
        contents: this._pageContents,
        diffs: this._pageDiffs,
        diacritics: this._hasDiacritics
      };
    }
    if (type === "cancelDelete") {
      this._extractTextPromises = this.#savedPageData.promises;
      this._pageContents = this.#savedPageData.contents;
      this._pageDiffs = this.#savedPageData.diffs;
      this._hasDiacritics = this.#savedPageData.diacritics;
      return;
    }
    if (type === "cleanSavedData") {
      this.#savedPageData = null;
      return;
    }
    if (this._findTimeout) {
      clearTimeout(this._findTimeout);
      this._findTimeout = null;
    }
    this._resumePageIdx = null;
    this._dirtyMatch = true;
    const prevPromises = this._extractTextPromises;
    const prevContents = this._pageContents;
    const prevDiffs = this._pageDiffs;
    const prevDiacritics = this._hasDiacritics;
    const extractTextPromises = this._extractTextPromises = [];
    const pageContents = this._pageContents = [];
    const pageDiffs = this._pageDiffs = [];
    const hasDiacritics = this._hasDiacritics = [];
    for (let i = 1, ii = pagesMapper.pagesNumber; i <= ii; i++) {
      const prevPageNumber = pagesMapper.getPrevPageNumber(i);
      if (prevPageNumber < 0) {
        const src = -prevPageNumber;
        extractTextPromises.push(this.#copiedPageData?.promises.get(src) || Promise.resolve());
        pageContents.push(this.#copiedPageData?.contents.get(src) ?? "");
        pageDiffs.push(this.#copiedPageData?.diffs.get(src) ?? null);
        hasDiacritics.push(this.#copiedPageData?.diacritics.get(src) ?? false);
        continue;
      }
      extractTextPromises.push(prevPromises[prevPageNumber - 1] || Promise.resolve());
      pageContents.push(prevContents[prevPageNumber - 1] ?? "");
      pageDiffs.push(prevDiffs[prevPageNumber - 1] ?? null);
      hasDiacritics.push(prevDiacritics[prevPageNumber - 1] ?? false);
    }
    if (this.#state) {
      this.#nextMatch();
    }
  }
  #onFindBarClose(evt) {
    const pdfDocument = this._pdfDocument;
    this._firstPageCapability.promise.then(() => {
      if (!this._pdfDocument || pdfDocument && this._pdfDocument !== pdfDocument) {
        return;
      }
      if (this._findTimeout) {
        clearTimeout(this._findTimeout);
        this._findTimeout = null;
      }
      if (this._resumePageIdx) {
        this._resumePageIdx = null;
        this._dirtyMatch = true;
      }
      this.#updateUIState(FindState.FOUND);
      this._highlightMatches = false;
      this.#updateAllPages();
    });
  }
  #requestMatchesCount() {
    const {
      pageIdx,
      matchIdx
    } = this._selected;
    let current = 0,
      total = this._matchesCountTotal;
    if (matchIdx !== -1) {
      for (let i = 0; i < pageIdx; i++) {
        current += this._pageMatches[i]?.length || 0;
      }
      current += matchIdx + 1;
    }
    if (current < 1 || current > total) {
      current = total = 0;
    }
    return {
      current,
      total
    };
  }
  #updateUIResultsCount() {
    this._eventBus.dispatch("updatefindmatchescount", {
      source: this,
      matchesCount: this.#requestMatchesCount()
    });
  }
  #updateUIState(state, previous = false) {
    if (!this.#updateMatchesCountOnProgress && (this.#visitedPagesCount !== this._linkService.pagesCount || state === FindState.PENDING)) {
      return;
    }
    this._eventBus.dispatch("updatefindcontrolstate", {
      source: this,
      state,
      previous,
      entireWord: this.#state?.entireWord ?? null,
      matchesCount: this.#requestMatchesCount(),
      rawQuery: this.#state?.query ?? null
    });
  }
}

;// ./web/pdf_find_bar.js


const MATCHES_COUNT_LIMIT = 1000;
class PDFFindBar {
  #mainContainer;
  #resizeObserver = new ResizeObserver(this.#resizeObserverCallback.bind(this));
  opened = false;
  constructor(options, mainContainer, eventBus) {
    this.bar = options.bar;
    this.toggleButton = options.toggleButton;
    this.findField = options.findField;
    this.highlightAll = options.highlightAllCheckbox;
    this.caseSensitive = options.caseSensitiveCheckbox;
    this.matchDiacritics = options.matchDiacriticsCheckbox;
    this.entireWord = options.entireWordCheckbox;
    this.findMsg = options.findMsg;
    this.findResultsCount = options.findResultsCount;
    this.findPreviousButton = options.findPreviousButton;
    this.findNextButton = options.findNextButton;
    this.eventBus = eventBus;
    this.#mainContainer = mainContainer;
    const checkedInputs = new Map([[this.highlightAll, "highlightallchange"], [this.caseSensitive, "casesensitivitychange"], [this.entireWord, "entirewordchange"], [this.matchDiacritics, "diacriticmatchingchange"]]);
    this.toggleButton.addEventListener("click", () => {
      this.toggle();
    });
    this.findField.addEventListener("input", () => {
      this.dispatchEvent("");
    });
    this.bar.addEventListener("keydown", ({
      keyCode,
      shiftKey,
      target
    }) => {
      switch (keyCode) {
        case 13:
          if (target === this.findField) {
            this.dispatchEvent("again", shiftKey);
          } else if (checkedInputs.has(target)) {
            target.checked = !target.checked;
            this.dispatchEvent(checkedInputs.get(target));
          }
          break;
        case 27:
          this.close();
          break;
      }
    });
    this.findPreviousButton.addEventListener("click", () => {
      this.dispatchEvent("again", true);
    });
    this.findNextButton.addEventListener("click", () => {
      this.dispatchEvent("again", false);
    });
    for (const [elem, evtName] of checkedInputs) {
      elem.addEventListener("click", () => {
        this.dispatchEvent(evtName);
      });
    }
  }
  reset() {
    this.updateUIState();
  }
  dispatchEvent(type, findPrev = false) {
    this.eventBus.dispatch("find", {
      source: this,
      type,
      query: this.findField.value,
      caseSensitive: this.caseSensitive.checked,
      entireWord: this.entireWord.checked,
      highlightAll: this.highlightAll.checked,
      findPrevious: findPrev,
      matchDiacritics: this.matchDiacritics.checked
    });
  }
  updateUIState(state, previous, matchesCount) {
    const {
      findField,
      findMsg
    } = this;
    let findMsgId = "",
      status = "";
    switch (state) {
      case FindState.FOUND:
        break;
      case FindState.PENDING:
        status = "pending";
        break;
      case FindState.NOT_FOUND:
        findMsgId = "pdfjs-find-not-found";
        status = "notFound";
        break;
      case FindState.WRAPPED:
        findMsgId = previous ? "pdfjs-find-reached-top" : "pdfjs-find-reached-bottom";
        break;
    }
    findField.setAttribute("data-status", status);
    findField.setAttribute("aria-invalid", state === FindState.NOT_FOUND);
    findMsg.setAttribute("data-status", status);
    if (findMsgId) {
      findMsg.setAttribute("data-l10n-id", findMsgId);
    } else {
      findMsg.removeAttribute("data-l10n-id");
      findMsg.textContent = "";
    }
    this.updateResultsCount(matchesCount);
  }
  updateResultsCount({
    current = 0,
    total = 0
  } = {}) {
    const {
      findResultsCount
    } = this;
    if (total > 0) {
      const limit = MATCHES_COUNT_LIMIT;
      findResultsCount.setAttribute("data-l10n-id", total > limit ? "pdfjs-find-match-count-limit" : "pdfjs-find-match-count");
      findResultsCount.setAttribute("data-l10n-args", JSON.stringify({
        limit,
        current,
        total
      }));
    } else {
      findResultsCount.removeAttribute("data-l10n-id");
      findResultsCount.textContent = "";
    }
  }
  open() {
    if (!this.opened) {
      this.#resizeObserver.observe(this.#mainContainer);
      this.#resizeObserver.observe(this.bar);
      this.opened = true;
      toggleExpandedBtn(this.toggleButton, true, this.bar);
    }
    this.findField.select();
    this.findField.focus();
  }
  close() {
    if (!this.opened) {
      return;
    }
    this.#resizeObserver.disconnect();
    this.opened = false;
    toggleExpandedBtn(this.toggleButton, false, this.bar);
    this.eventBus.dispatch("findbarclose", {
      source: this
    });
  }
  toggle() {
    if (this.opened) {
      this.close();
    } else {
      this.open();
    }
  }
  #resizeObserverCallback() {
    const {
      bar
    } = this;
    bar.classList.remove("wrapContainers");
    const findbarHeight = bar.clientHeight;
    const inputContainerHeight = bar.firstElementChild.clientHeight;
    if (findbarHeight > inputContainerHeight) {
      bar.classList.add("wrapContainers");
    }
  }
}

;// ./web/pdf_history.js




const HASH_CHANGE_TIMEOUT = 1000;
const POSITION_UPDATED_THRESHOLD = 50;
const UPDATE_VIEWAREA_TIMEOUT = 1000;
function getCurrentHash() {
  return document.location.hash;
}
class PDFHistory {
  #eventAC = null;
  constructor({
    linkService,
    eventBus
  }) {
    this.linkService = linkService;
    this.eventBus = eventBus;
    this._initialized = false;
    this._fingerprint = "";
    this.reset();
    this.eventBus.on("pagesinit", () => {
      this._isPagesLoaded = false;
      this.eventBus.on("pagesloaded", evt => {
        this._isPagesLoaded = !!evt.pagesCount;
      }, {
        once: true,
        ...internalOpt
      });
    }, internalOpt);
  }
  initialize({
    fingerprint,
    resetHistory = false,
    updateUrl = false
  }) {
    if (!fingerprint || typeof fingerprint !== "string") {
      console.error('PDFHistory.initialize: The "fingerprint" must be a non-empty string.');
      return;
    }
    if (this._initialized) {
      this.reset();
    }
    const reInitialized = this._fingerprint !== "" && this._fingerprint !== fingerprint;
    this._fingerprint = fingerprint;
    this._updateUrl = updateUrl === true;
    this._initialized = true;
    this.#bindEvents();
    const state = window.history.state;
    this._popStateInProgress = false;
    this._blockHashChange = 0;
    this._currentHash = getCurrentHash();
    this._numPositionUpdates = 0;
    this._uid = this._maxUid = 0;
    this._destination = null;
    this._position = null;
    if (!this.#isValidState(state, true) || resetHistory) {
      const {
        hash,
        page,
        rotation
      } = this.#parseCurrentHash(true);
      if (!hash || reInitialized || resetHistory) {
        this.#pushOrReplaceState(null, true);
        return;
      }
      this.#pushOrReplaceState({
        hash,
        page,
        rotation
      }, true);
      return;
    }
    const destination = state.destination;
    this.#updateInternalState(destination, state.uid, true);
    if (destination.rotation !== undefined) {
      this._initialRotation = destination.rotation;
    }
    if (destination.dest) {
      this._initialBookmark = JSON.stringify(destination.dest);
      this._destination.page = null;
    } else if (destination.hash) {
      this._initialBookmark = destination.hash;
    } else if (destination.page) {
      this._initialBookmark = `page=${destination.page}`;
    }
  }
  reset() {
    if (this._initialized) {
      this.#pageHide();
      this._initialized = false;
      this.#unbindEvents();
    }
    if (this._updateViewareaTimeout) {
      clearTimeout(this._updateViewareaTimeout);
      this._updateViewareaTimeout = null;
    }
    this._initialBookmark = null;
    this._initialRotation = null;
  }
  push({
    namedDest = null,
    explicitDest,
    pageNumber
  }) {
    if (!this._initialized) {
      return;
    }
    if (namedDest && typeof namedDest !== "string") {
      console.error("PDFHistory.push: " + `"${namedDest}" is not a valid namedDest parameter.`);
      return;
    } else if (!Array.isArray(explicitDest)) {
      console.error("PDFHistory.push: " + `"${explicitDest}" is not a valid explicitDest parameter.`);
      return;
    } else if (!this.#isValidPage(pageNumber)) {
      if (pageNumber !== null || this._destination) {
        console.error("PDFHistory.push: " + `"${pageNumber}" is not a valid pageNumber parameter.`);
        return;
      }
    }
    const hash = namedDest || JSON.stringify(explicitDest);
    if (!hash) {
      return;
    }
    let forceReplace = false;
    if (this._destination && (isDestHashesEqual(this._destination.hash, hash) || isDestArraysEqual(this._destination.dest, explicitDest))) {
      if (this._destination.page) {
        return;
      }
      forceReplace = true;
    }
    if (this._popStateInProgress && !forceReplace) {
      return;
    }
    this.#pushOrReplaceState({
      dest: explicitDest,
      hash,
      page: pageNumber,
      rotation: this.linkService.rotation
    }, forceReplace);
    if (!this._popStateInProgress) {
      this._popStateInProgress = true;
      Promise.resolve().then(() => {
        this._popStateInProgress = false;
      });
    }
  }
  pushPage(pageNumber) {
    if (!this._initialized) {
      return;
    }
    if (!this.#isValidPage(pageNumber)) {
      console.error(`PDFHistory.pushPage: "${pageNumber}" is not a valid page number.`);
      return;
    }
    if (this._destination?.page === pageNumber) {
      return;
    }
    if (this._popStateInProgress) {
      return;
    }
    this.#pushOrReplaceState({
      dest: null,
      hash: `page=${pageNumber}`,
      page: pageNumber,
      rotation: this.linkService.rotation
    });
    if (!this._popStateInProgress) {
      this._popStateInProgress = true;
      Promise.resolve().then(() => {
        this._popStateInProgress = false;
      });
    }
  }
  pushCurrentPosition() {
    if (!this._initialized || this._popStateInProgress) {
      return;
    }
    this.#tryPushCurrentPosition();
  }
  back() {
    if (!this._initialized || this._popStateInProgress) {
      return;
    }
    const state = window.history.state;
    if (this.#isValidState(state) && state.uid > 0) {
      window.history.back();
    }
  }
  forward() {
    if (!this._initialized || this._popStateInProgress) {
      return;
    }
    const state = window.history.state;
    if (this.#isValidState(state) && state.uid < this._maxUid) {
      window.history.forward();
    }
  }
  get popStateInProgress() {
    return this._initialized && (this._popStateInProgress || this._blockHashChange > 0);
  }
  get initialBookmark() {
    return this._initialized ? this._initialBookmark : null;
  }
  get initialRotation() {
    return this._initialized ? this._initialRotation : null;
  }
  #pushOrReplaceState(destination, forceReplace = false) {
    const shouldReplace = forceReplace || !this._destination;
    const newState = {
      fingerprint: this._fingerprint,
      uid: shouldReplace ? this._uid : this._uid + 1,
      destination
    };
    this.#updateInternalState(destination, newState.uid);
    let newUrl;
    if (this._updateUrl && destination?.hash) {
      const {
        href,
        protocol
      } = document.location;
      if (protocol !== "file:") {
        newUrl = updateUrlHash(href, destination.hash);
      }
    }
    if (shouldReplace) {
      window.history.replaceState(newState, "", newUrl);
    } else {
      window.history.pushState(newState, "", newUrl);
    }
  }
  #tryPushCurrentPosition(temporary = false) {
    if (!this._position) {
      return;
    }
    let position = this._position;
    if (temporary) {
      position = Object.assign(Object.create(null), this._position);
      position.temporary = true;
    }
    if (!this._destination) {
      this.#pushOrReplaceState(position);
      return;
    }
    if (this._destination.temporary) {
      this.#pushOrReplaceState(position, true);
      return;
    }
    if (this._destination.hash === position.hash) {
      return;
    }
    if (!this._destination.page && ( false || this._numPositionUpdates <= POSITION_UPDATED_THRESHOLD)) {
      return;
    }
    let forceReplace = false;
    if (this._destination.page >= position.first && this._destination.page <= position.page) {
      if (this._destination.dest !== undefined || !this._destination.first) {
        return;
      }
      forceReplace = true;
    }
    this.#pushOrReplaceState(position, forceReplace);
  }
  #isValidPage(val) {
    return Number.isInteger(val) && val > 0 && val <= this.linkService.pagesCount;
  }
  #isValidState(state, checkReload = false) {
    if (!state) {
      return false;
    }
    if (state.fingerprint !== this._fingerprint) {
      if (checkReload) {
        if (typeof state.fingerprint !== "string" || state.fingerprint.length !== this._fingerprint.length) {
          return false;
        }
        const [perfEntry] = performance.getEntriesByType("navigation");
        if (perfEntry?.type !== "reload") {
          return false;
        }
      } else {
        return false;
      }
    }
    if (!Number.isInteger(state.uid) || state.uid < 0 || state.destination === null || typeof state.destination !== "object") {
      return false;
    }
    return true;
  }
  #updateInternalState(destination, uid, removeTemporary = false) {
    if (this._updateViewareaTimeout) {
      clearTimeout(this._updateViewareaTimeout);
      this._updateViewareaTimeout = null;
    }
    if (removeTemporary && destination?.temporary) {
      delete destination.temporary;
    }
    this._destination = destination;
    this._uid = uid;
    this._maxUid = Math.max(this._maxUid, uid);
    this._numPositionUpdates = 0;
  }
  #parseCurrentHash(checkNameddest = false) {
    const hash = unescape(getCurrentHash()).substring(1);
    const params = parseQueryString(hash);
    const nameddest = params.get("nameddest") || "";
    let page = params.get("page") | 0;
    if (!this.#isValidPage(page) || checkNameddest && nameddest.length > 0) {
      page = null;
    }
    return {
      hash,
      page,
      rotation: this.linkService.rotation
    };
  }
  #updateViewarea({
    location
  }) {
    if (this._updateViewareaTimeout) {
      clearTimeout(this._updateViewareaTimeout);
      this._updateViewareaTimeout = null;
    }
    this._position = {
      hash: location.pdfOpenParams.substring(1),
      page: this.linkService.page,
      first: location.pageNumber,
      rotation: location.rotation
    };
    if (this._popStateInProgress) {
      return;
    }
    if ( true && this._isPagesLoaded && this._destination && !this._destination.page) {
      this._numPositionUpdates++;
    }
    if (true) {
      this._updateViewareaTimeout = setTimeout(() => {
        if (!this._popStateInProgress) {
          this.#tryPushCurrentPosition(true);
        }
        this._updateViewareaTimeout = null;
      }, UPDATE_VIEWAREA_TIMEOUT);
    }
  }
  #popState({
    state
  }) {
    const newHash = getCurrentHash(),
      hashChanged = this._currentHash !== newHash;
    this._currentHash = newHash;
    if (!state) {
      this._uid++;
      const {
        hash,
        page,
        rotation
      } = this.#parseCurrentHash();
      this.#pushOrReplaceState({
        hash,
        page,
        rotation
      }, true);
      return;
    }
    if (!this.#isValidState(state)) {
      return;
    }
    this._popStateInProgress = true;
    if (hashChanged) {
      this._blockHashChange++;
      waitOnEventOrTimeout({
        target: window,
        name: "hashchange",
        delay: HASH_CHANGE_TIMEOUT
      }).then(() => {
        this._blockHashChange--;
      });
    }
    const destination = state.destination;
    this.#updateInternalState(destination, state.uid, true);
    if (isValidRotation(destination.rotation)) {
      this.linkService.rotation = destination.rotation;
    }
    if (destination.dest) {
      this.linkService.goToDestination(destination.dest);
    } else if (destination.hash) {
      this.linkService.setHash(destination.hash);
    } else if (destination.page) {
      this.linkService.page = destination.page;
    }
    Promise.resolve().then(() => {
      this._popStateInProgress = false;
    });
  }
  #pageHide() {
    if (!this._destination || this._destination.temporary) {
      this.#tryPushCurrentPosition();
    }
  }
  #bindEvents() {
    if (this.#eventAC) {
      return;
    }
    this.#eventAC = new AbortController();
    const {
      signal
    } = this.#eventAC;
    this.eventBus.on("updateviewarea", this.#updateViewarea.bind(this), {
      signal,
      ...internalOpt
    });
    window.addEventListener("popstate", this.#popState.bind(this), {
      signal
    });
    window.addEventListener("pagehide", this.#pageHide.bind(this), {
      signal
    });
  }
  #unbindEvents() {
    this.#eventAC?.abort();
    this.#eventAC = null;
  }
}
function isDestHashesEqual(destHash, pushHash) {
  if (typeof destHash !== "string" || typeof pushHash !== "string") {
    return false;
  }
  if (destHash === pushHash) {
    return true;
  }
  const nameddest = parseQueryString(destHash).get("nameddest");
  if (nameddest === pushHash) {
    return true;
  }
  return false;
}
function isDestArraysEqual(firstDest, secondDest) {
  function isEntryEqual(first, second) {
    if (typeof first !== typeof second || Array.isArray(first) || Array.isArray(second)) {
      return false;
    }
    if (first !== null && typeof first === "object" && second !== null) {
      if (Object.keys(first).length !== Object.keys(second).length) {
        return false;
      }
      for (const key in first) {
        if (!isEntryEqual(first[key], second[key])) {
          return false;
        }
      }
      return true;
    }
    return first === second || Number.isNaN(first) && Number.isNaN(second);
  }
  if (!(Array.isArray(firstDest) && Array.isArray(secondDest))) {
    return false;
  }
  if (firstDest.length !== secondDest.length) {
    return false;
  }
  for (let i = 0, ii = firstDest.length; i < ii; i++) {
    if (!isEntryEqual(firstDest[i], secondDest[i])) {
      return false;
    }
  }
  return true;
}

;// ./web/pdf_layer_viewer.js


class PDFLayerViewer extends BaseTreeViewer {
  constructor(options) {
    super(options);
    const {
      eventBus
    } = this;
    eventBus.on("optionalcontentconfigchanged", evt => {
      this.#updateLayers(evt.promise);
    }, internalOpt);
    eventBus.on("resetlayers", () => {
      this.#updateLayers();
    }, internalOpt);
    eventBus.on("togglelayerstree", this._toggleAllTreeItems.bind(this), internalOpt);
  }
  reset() {
    super.reset();
    this._optionalContentConfig = null;
    this._optionalContentVisibility?.clear();
    this._optionalContentVisibility = null;
  }
  _dispatchEvent(layersCount) {
    this.eventBus.dispatch("layersloaded", {
      source: this,
      layersCount
    });
  }
  _bindLink(element, {
    groupId,
    input
  }) {
    const setVisibility = () => {
      const visible = input.checked;
      this._optionalContentConfig.setVisibility(groupId, visible);
      const cached = this._optionalContentVisibility.get(groupId);
      if (cached) {
        cached.visible = visible;
      }
      this.eventBus.dispatch("optionalcontentconfig", {
        source: this,
        promise: Promise.resolve(this._optionalContentConfig)
      });
    };
    element.onclick = evt => {
      if (evt.target === input) {
        setVisibility();
        return true;
      } else if (evt.target !== element) {
        return true;
      }
      input.checked = !input.checked;
      setVisibility();
      return false;
    };
  }
  _setNestedName(element, {
    name = null
  }) {
    if (typeof name === "string") {
      element.textContent = this._normalizeTextContent(name);
      return;
    }
    element.setAttribute("data-l10n-id", "pdfjs-additional-layers");
    element.style.fontStyle = "italic";
    this._l10n.translateOnce(element);
  }
  _addToggleButton(div, {
    name = null
  }) {
    super._addToggleButton(div, name === null);
  }
  _toggleAllTreeItems() {
    if (!this._optionalContentConfig) {
      return;
    }
    super._toggleAllTreeItems();
  }
  render({
    optionalContentConfig,
    pdfDocument
  }) {
    if (this._optionalContentConfig) {
      this.reset();
    }
    this._optionalContentConfig = optionalContentConfig || null;
    this._pdfDocument = pdfDocument || null;
    const groups = optionalContentConfig?.getOrder();
    if (!groups) {
      this._dispatchEvent(0);
      return;
    }
    this._optionalContentVisibility = new Map();
    const fragment = document.createDocumentFragment(),
      queue = [{
        parent: fragment,
        groups
      }];
    let layersCount = 0,
      hasAnyNesting = false;
    while (queue.length > 0) {
      const levelData = queue.shift();
      for (const groupId of levelData.groups) {
        const div = document.createElement("div");
        div.className = "treeItem";
        const element = document.createElement("a");
        div.append(element);
        if (typeof groupId === "object") {
          hasAnyNesting = true;
          this._addToggleButton(div, groupId);
          this._setNestedName(element, groupId);
          const itemsDiv = document.createElement("div");
          itemsDiv.className = "treeItems";
          div.append(itemsDiv);
          queue.push({
            parent: itemsDiv,
            groups: groupId.order
          });
        } else {
          const group = optionalContentConfig.getGroup(groupId);
          const label = document.createElement("label");
          const input = document.createElement("input");
          label.append(input, document.createTextNode(this._normalizeTextContent(group.name)));
          this._bindLink(element, {
            groupId,
            input
          });
          input.type = "checkbox";
          input.checked = group.visible;
          this._optionalContentVisibility.set(groupId, {
            input,
            visible: input.checked
          });
          element.append(label);
          layersCount++;
        }
        levelData.parent.append(div);
      }
    }
    this._finishRendering(fragment, layersCount, hasAnyNesting);
  }
  async #updateLayers(promise = null) {
    if (!this._optionalContentConfig) {
      return;
    }
    const pdfDocument = this._pdfDocument;
    const optionalContentConfig = await (promise || pdfDocument.getOptionalContentConfig({
      intent: "display"
    }));
    if (pdfDocument !== this._pdfDocument) {
      return;
    }
    if (promise) {
      for (const [groupId, cached] of this._optionalContentVisibility) {
        const group = optionalContentConfig.getGroup(groupId);
        if (group && cached.visible !== group.visible) {
          cached.input.checked = cached.visible = !cached.visible;
        }
      }
      return;
    }
    this.eventBus.dispatch("optionalcontentconfig", {
      source: this,
      promise: Promise.resolve(optionalContentConfig)
    });
    this.render({
      optionalContentConfig,
      pdfDocument: this._pdfDocument
    });
  }
}

;// ./web/pdf_outline_viewer.js



class PDFOutlineViewer extends BaseTreeViewer {
  constructor(options) {
    super(options);
    this.linkService = options.linkService;
    this.downloadManager = options.downloadManager;
    const {
      eventBus
    } = this;
    eventBus.on("toggleoutlinetree", this._toggleAllTreeItems.bind(this), internalOpt);
    eventBus.on("currentoutlineitem", this._currentOutlineItem.bind(this), internalOpt);
    eventBus.on("pagechanging", evt => {
      this._currentPageNumber = evt.pageNumber;
    }, internalOpt);
    eventBus.on("pagesloaded", evt => {
      this._isPagesLoaded = !!evt.pagesCount;
      this._currentOutlineItemCapability?.resolve(this._isPagesLoaded);
    }, internalOpt);
    eventBus.on("sidebarviewchanged", evt => {
      this._sidebarView = evt.view;
    }, internalOpt);
  }
  reset() {
    super.reset();
    this._outline = null;
    this._pageNumberToDestHashCapability = null;
    this._currentPageNumber = 1;
    this._isPagesLoaded = null;
    this._currentOutlineItemCapability?.resolve(false);
    this._currentOutlineItemCapability = null;
  }
  _dispatchEvent(outlineCount) {
    this._currentOutlineItemCapability = Promise.withResolvers();
    if (outlineCount === 0 || this._pdfDocument?.loadingParams.disableAutoFetch) {
      this._currentOutlineItemCapability.resolve(false);
    } else if (this._isPagesLoaded !== null) {
      this._currentOutlineItemCapability.resolve(this._isPagesLoaded);
    }
    this.eventBus.dispatch("outlineloaded", {
      source: this,
      outlineCount,
      currentOutlineItemPromise: this._currentOutlineItemCapability.promise
    });
  }
  _bindLink(element, {
    url,
    newWindow,
    action,
    attachmentId,
    attachment,
    dest,
    setOCGState
  }) {
    const {
      linkService
    } = this;
    if (url) {
      linkService.addLinkAttributes(element, url, newWindow);
      return;
    }
    if (action) {
      element.href = linkService.getAnchorUrl("");
      element.onclick = () => {
        linkService.executeNamedAction(action);
        return false;
      };
      return;
    }
    if (attachmentId && attachment) {
      element.href = linkService.getAnchorUrl("");
      const openAttachment = async () => {
        const content = await linkService.getAttachmentContent(attachmentId);
        if (content) {
          this.downloadManager?.openOrDownloadData(content, attachment.filename);
        }
      };
      element.onclick = () => {
        openAttachment();
        return false;
      };
      return;
    }
    if (setOCGState) {
      element.href = linkService.getAnchorUrl("");
      element.onclick = () => {
        linkService.executeSetOCGState(setOCGState);
        return false;
      };
      return;
    }
    element.href = linkService.getDestinationHash(dest);
    element.onclick = evt => {
      this._updateCurrentTreeItem(evt.target.parentNode);
      if (dest) {
        linkService.goToDestination(dest);
      }
      return false;
    };
  }
  _setStyles(element, {
    bold,
    italic
  }) {
    if (bold) {
      element.style.fontWeight = "bold";
    }
    if (italic) {
      element.style.fontStyle = "italic";
    }
  }
  _addToggleButton(div, {
    count,
    items
  }) {
    let hidden = false;
    if (count < 0) {
      let totalCount = items.length;
      if (totalCount > 0) {
        const queue = [...items];
        while (queue.length > 0) {
          const {
            count: nestedCount,
            items: nestedItems
          } = queue.shift();
          if (nestedCount > 0 && nestedItems.length > 0) {
            totalCount += nestedItems.length;
            queue.push(...nestedItems);
          }
        }
      }
      if (Math.abs(count) === totalCount) {
        hidden = true;
      }
    }
    super._addToggleButton(div, hidden);
  }
  _toggleAllTreeItems() {
    if (!this._outline) {
      return;
    }
    super._toggleAllTreeItems();
  }
  render({
    outline,
    pdfDocument
  }) {
    if (this._outline) {
      this.reset();
    }
    this._outline = outline || null;
    this._pdfDocument = pdfDocument || null;
    if (!outline) {
      this._dispatchEvent(0);
      return;
    }
    const fragment = document.createDocumentFragment();
    const queue = [{
      parent: fragment,
      items: outline
    }];
    let outlineCount = 0,
      hasAnyNesting = false;
    while (queue.length > 0) {
      const levelData = queue.shift();
      for (const item of levelData.items) {
        const div = document.createElement("div");
        div.className = "treeItem";
        const element = document.createElement("a");
        this._bindLink(element, item);
        this._setStyles(element, item);
        element.textContent = this._normalizeTextContent(item.title);
        div.append(element);
        if (item.items.length > 0) {
          hasAnyNesting = true;
          this._addToggleButton(div, item);
          const itemsDiv = document.createElement("div");
          itemsDiv.className = "treeItems";
          div.append(itemsDiv);
          queue.push({
            parent: itemsDiv,
            items: item.items
          });
        }
        levelData.parent.append(div);
        outlineCount++;
      }
    }
    this._finishRendering(fragment, outlineCount, hasAnyNesting);
  }
  async _currentOutlineItem() {
    if (!this._isPagesLoaded) {
      throw new Error("_currentOutlineItem: All pages have not been loaded.");
    }
    if (!this._outline || !this._pdfDocument) {
      return;
    }
    const pageNumberToDestHash = await this._getPageNumberToDestHash(this._pdfDocument);
    if (!pageNumberToDestHash) {
      return;
    }
    this._updateCurrentTreeItem(null);
    if (this._sidebarView !== SidebarView.OUTLINE) {
      return;
    }
    for (let i = this._currentPageNumber; i > 0; i--) {
      const destHash = pageNumberToDestHash.get(i);
      if (!destHash) {
        continue;
      }
      const linkElement = this.container.querySelector(`a[href="${destHash}"]`);
      if (!linkElement) {
        continue;
      }
      this._scrollToCurrentTreeItem(linkElement.parentNode);
      break;
    }
  }
  async _getPageNumberToDestHash(pdfDocument) {
    if (this._pageNumberToDestHashCapability) {
      return this._pageNumberToDestHashCapability.promise;
    }
    this._pageNumberToDestHashCapability = Promise.withResolvers();
    const pageNumberToDestHash = new Map(),
      pageNumberNesting = new Map();
    const queue = [{
      nesting: 0,
      items: this._outline
    }];
    while (queue.length > 0) {
      const levelData = queue.shift(),
        currentNesting = levelData.nesting;
      for (const {
        dest,
        items
      } of levelData.items) {
        let explicitDest, pageNumber;
        if (typeof dest === "string") {
          explicitDest = await pdfDocument.getDestination(dest);
          if (pdfDocument !== this._pdfDocument) {
            return null;
          }
        } else {
          explicitDest = dest;
        }
        if (Array.isArray(explicitDest)) {
          const [destRef] = explicitDest;
          if (destRef && typeof destRef === "object") {
            pageNumber = pdfDocument.cachedPageNumber(destRef);
          } else if (Number.isInteger(destRef)) {
            pageNumber = destRef + 1;
          }
          if (Number.isInteger(pageNumber) && (!pageNumberToDestHash.has(pageNumber) || currentNesting > pageNumberNesting.get(pageNumber))) {
            const destHash = this.linkService.getDestinationHash(dest);
            pageNumberToDestHash.set(pageNumber, destHash);
            pageNumberNesting.set(pageNumber, currentNesting);
          }
        }
        if (items.length > 0) {
          queue.push({
            nesting: currentNesting + 1,
            items
          });
        }
      }
    }
    this._pageNumberToDestHashCapability.resolve(pageNumberToDestHash.size > 0 ? pageNumberToDestHash : null);
    return this._pageNumberToDestHashCapability.promise;
  }
}

;// ./web/pdf_presentation_mode.js


const DELAY_BEFORE_HIDING_CONTROLS = 3000;
const ACTIVE_SELECTOR = "pdfPresentationMode";
const CONTROLS_SELECTOR = "pdfPresentationModeControls";
const MOUSE_SCROLL_COOLDOWN_TIME = 50;
const PAGE_SWITCH_THRESHOLD = 0.1;
const SWIPE_MIN_DISTANCE_THRESHOLD = 50;
const SWIPE_ANGLE_THRESHOLD = Math.PI / 6;
class PDFPresentationMode {
  #state = PresentationModeState.UNKNOWN;
  #args = null;
  #fullscreenChangeAC = null;
  #windowAC = null;
  constructor({
    container,
    pdfViewer,
    eventBus
  }) {
    this.container = container;
    this.pdfViewer = pdfViewer;
    this.eventBus = eventBus;
    this.contextMenuOpen = false;
    this.mouseScrollTimeStamp = 0;
    this.mouseScrollDelta = 0;
    this.touchSwipeState = null;
  }
  async request() {
    const {
      container,
      pdfViewer
    } = this;
    if (this.active || !pdfViewer.pagesCount || !container.requestFullscreen) {
      return false;
    }
    this.#addFullscreenChangeListeners();
    this.#notifyStateChange(PresentationModeState.CHANGING);
    const promise = container.requestFullscreen();
    this.#args = {
      pageNumber: pdfViewer.currentPageNumber,
      scaleValue: pdfViewer.currentScaleValue,
      scrollMode: pdfViewer.scrollMode,
      spreadMode: null,
      annotationEditorMode: null
    };
    if (pdfViewer.spreadMode !== SpreadMode.NONE && !(pdfViewer.pageViewsReady && pdfViewer.hasEqualPageSizes)) {
      console.warn("Ignoring Spread modes when entering PresentationMode, " + "since the document may contain varying page sizes.");
      this.#args.spreadMode = pdfViewer.spreadMode;
    }
    if (pdfViewer.annotationEditorMode !== AnnotationEditorType.DISABLE) {
      this.#args.annotationEditorMode = pdfViewer.annotationEditorMode;
    }
    try {
      await promise;
      pdfViewer.focus();
      return true;
    } catch {
      this.#removeFullscreenChangeListeners();
      this.#notifyStateChange(PresentationModeState.NORMAL);
    }
    return false;
  }
  get active() {
    return this.#state === PresentationModeState.CHANGING || this.#state === PresentationModeState.FULLSCREEN;
  }
  #mouseWheel(evt) {
    if (!this.active || evt.target.closest?.(".mediaAnnotation")) {
      return;
    }
    evt.preventDefault();
    const delta = normalizeWheelEventDelta(evt);
    const currentTime = Date.now();
    const storedTime = this.mouseScrollTimeStamp;
    if (currentTime > storedTime && currentTime - storedTime < MOUSE_SCROLL_COOLDOWN_TIME) {
      return;
    }
    if (this.mouseScrollDelta > 0 && delta < 0 || this.mouseScrollDelta < 0 && delta > 0) {
      this.#resetMouseScrollState();
    }
    this.mouseScrollDelta += delta;
    if (Math.abs(this.mouseScrollDelta) >= PAGE_SWITCH_THRESHOLD) {
      const totalDelta = this.mouseScrollDelta;
      this.#resetMouseScrollState();
      const success = totalDelta > 0 ? this.pdfViewer.previousPage() : this.pdfViewer.nextPage();
      if (success) {
        this.mouseScrollTimeStamp = currentTime;
      }
    }
  }
  #notifyStateChange(state) {
    this.#state = state;
    this.eventBus.dispatch("presentationmodechanged", {
      source: this,
      state
    });
  }
  #enter() {
    this.#notifyStateChange(PresentationModeState.FULLSCREEN);
    this.container.classList.add(ACTIVE_SELECTOR);
    setTimeout(() => {
      this.pdfViewer.scrollMode = ScrollMode.PAGE;
      if (this.#args.spreadMode !== null) {
        this.pdfViewer.spreadMode = SpreadMode.NONE;
      }
      this.pdfViewer.currentPageNumber = this.#args.pageNumber;
      this.pdfViewer.currentScaleValue = "page-fit";
      if (this.#args.annotationEditorMode !== null) {
        this.pdfViewer.annotationEditorMode = {
          mode: AnnotationEditorType.NONE
        };
      }
    }, 0);
    this.#addWindowListeners();
    this.#showControls();
    this.contextMenuOpen = false;
    document.getSelection().empty();
  }
  #exit() {
    const pageNumber = this.pdfViewer.currentPageNumber;
    this.container.classList.remove(ACTIVE_SELECTOR);
    setTimeout(() => {
      this.#removeFullscreenChangeListeners();
      this.#notifyStateChange(PresentationModeState.NORMAL);
      this.pdfViewer.scrollMode = this.#args.scrollMode;
      if (this.#args.spreadMode !== null) {
        this.pdfViewer.spreadMode = this.#args.spreadMode;
      }
      this.pdfViewer.currentScaleValue = this.#args.scaleValue;
      this.pdfViewer.currentPageNumber = pageNumber;
      if (this.#args.annotationEditorMode !== null) {
        this.pdfViewer.annotationEditorMode = {
          mode: this.#args.annotationEditorMode
        };
      }
      this.#args = null;
    }, 0);
    this.#removeWindowListeners();
    this.#hideControls();
    this.#resetMouseScrollState();
    this.contextMenuOpen = false;
  }
  #mouseDown(evt) {
    if (this.contextMenuOpen) {
      this.contextMenuOpen = false;
      evt.preventDefault();
      return;
    }
    if (evt.button !== 0) {
      return;
    }
    if (evt.target.href && evt.target.parentNode?.hasAttribute("data-internal-link")) {
      return;
    }
    if (evt.target.closest?.(".mediaAnnotation")) {
      return;
    }
    evt.preventDefault();
    if (evt.shiftKey) {
      this.pdfViewer.previousPage();
    } else {
      this.pdfViewer.nextPage();
    }
  }
  #contextMenu() {
    this.contextMenuOpen = true;
  }
  #showControls() {
    if (this.controlsTimeout) {
      clearTimeout(this.controlsTimeout);
    } else {
      this.container.classList.add(CONTROLS_SELECTOR);
    }
    this.controlsTimeout = setTimeout(() => {
      this.container.classList.remove(CONTROLS_SELECTOR);
      delete this.controlsTimeout;
    }, DELAY_BEFORE_HIDING_CONTROLS);
  }
  #hideControls() {
    if (!this.controlsTimeout) {
      return;
    }
    clearTimeout(this.controlsTimeout);
    this.container.classList.remove(CONTROLS_SELECTOR);
    delete this.controlsTimeout;
  }
  #resetMouseScrollState() {
    this.mouseScrollTimeStamp = 0;
    this.mouseScrollDelta = 0;
  }
  #touchSwipe(evt) {
    if (!this.active) {
      return;
    }
    if (evt.target.closest?.(".mediaAnnotation")) {
      this.touchSwipeState = null;
      return;
    }
    if (evt.touches.length > 1) {
      this.touchSwipeState = null;
      return;
    }
    switch (evt.type) {
      case "touchstart":
        this.touchSwipeState = {
          startX: evt.touches[0].pageX,
          startY: evt.touches[0].pageY,
          endX: evt.touches[0].pageX,
          endY: evt.touches[0].pageY
        };
        break;
      case "touchmove":
        if (this.touchSwipeState === null) {
          return;
        }
        this.touchSwipeState.endX = evt.touches[0].pageX;
        this.touchSwipeState.endY = evt.touches[0].pageY;
        evt.preventDefault();
        break;
      case "touchend":
        if (this.touchSwipeState === null) {
          return;
        }
        let delta = 0;
        const dx = this.touchSwipeState.endX - this.touchSwipeState.startX;
        const dy = this.touchSwipeState.endY - this.touchSwipeState.startY;
        const absAngle = Math.abs(Math.atan2(dy, dx));
        if (Math.abs(dx) > SWIPE_MIN_DISTANCE_THRESHOLD && (absAngle <= SWIPE_ANGLE_THRESHOLD || absAngle >= Math.PI - SWIPE_ANGLE_THRESHOLD)) {
          delta = dx;
        } else if (Math.abs(dy) > SWIPE_MIN_DISTANCE_THRESHOLD && Math.abs(absAngle - Math.PI / 2) <= SWIPE_ANGLE_THRESHOLD) {
          delta = dy;
        }
        if (delta > 0) {
          this.pdfViewer.previousPage();
        } else if (delta < 0) {
          this.pdfViewer.nextPage();
        }
        break;
    }
  }
  #addWindowListeners() {
    if (this.#windowAC) {
      return;
    }
    this.#windowAC = new AbortController();
    const {
      signal
    } = this.#windowAC;
    const touchSwipeBind = this.#touchSwipe.bind(this);
    window.addEventListener("mousemove", this.#showControls.bind(this), {
      signal
    });
    window.addEventListener("mousedown", this.#mouseDown.bind(this), {
      signal
    });
    window.addEventListener("wheel", this.#mouseWheel.bind(this), {
      passive: false,
      signal
    });
    window.addEventListener("keydown", this.#resetMouseScrollState.bind(this), {
      signal
    });
    window.addEventListener("contextmenu", this.#contextMenu.bind(this), {
      signal
    });
    window.addEventListener("touchstart", touchSwipeBind, {
      signal
    });
    window.addEventListener("touchmove", touchSwipeBind, {
      signal
    });
    window.addEventListener("touchend", touchSwipeBind, {
      signal
    });
  }
  #removeWindowListeners() {
    this.#windowAC?.abort();
    this.#windowAC = null;
  }
  #addFullscreenChangeListeners() {
    if (this.#fullscreenChangeAC) {
      return;
    }
    this.#fullscreenChangeAC = new AbortController();
    window.addEventListener("fullscreenchange", () => {
      if (document.fullscreenElement) {
        this.#enter();
      } else {
        this.#exit();
      }
    }, {
      signal: this.#fullscreenChangeAC.signal
    });
  }
  #removeFullscreenChangeListeners() {
    this.#fullscreenChangeAC?.abort();
    this.#fullscreenChangeAC = null;
  }
}

;// ./web/xfa_layer_builder.js

class XfaLayerBuilder {
  #cancelled = false;
  div = null;
  constructor({
    pdfPage,
    annotationStorage = null,
    linkService,
    xfaHtml = null
  }) {
    this.pdfPage = pdfPage;
    this.annotationStorage = annotationStorage;
    this.linkService = linkService;
    this.xfaHtml = xfaHtml;
  }
  async render({
    viewport,
    intent = "display"
  }) {
    let xfaHtml;
    if (intent === "print") {
      xfaHtml = this.xfaHtml;
    } else {
      xfaHtml = await this.pdfPage.getXfa();
      if (this.#cancelled || !xfaHtml) {
        return {
          textDivs: []
        };
      }
    }
    const hasDiv = !!this.div;
    const params = {
      viewport: viewport.clone({
        dontFlip: true
      }),
      div: this.div ??= document.createElement("div"),
      xfaHtml,
      annotationStorage: this.annotationStorage,
      linkService: this.linkService,
      intent
    };
    return hasDiv ? XfaLayer.update(params) : XfaLayer.render(params);
  }
  cancel() {
    this.#cancelled = true;
  }
  hide() {
    if (!this.div) {
      return;
    }
    this.div.hidden = true;
  }
}

;// ./web/print_utils.js



class BasePrintServiceFactory {
  static initGlobals(app) {}
  static get supportsPrinting() {
    throw new Error("Not implemented: supportsPrinting");
  }
  static createPrintService(params) {
    throw new Error("Not implemented: createPrintService");
  }
}
function getXfaHtmlForPrinting(printContainer, pdfDocument) {
  const xfaHtml = pdfDocument.allXfaHtml;
  const linkService = new SimpleLinkService();
  const scale = Math.round(PixelsPerInch.PDF_TO_CSS_UNITS * 100) / 100;
  for (const xfaPage of xfaHtml.children) {
    const page = document.createElement("div");
    page.className = "xfaPrintedPage";
    printContainer.append(page);
    const builder = new XfaLayerBuilder({
      pdfPage: null,
      annotationStorage: pdfDocument.annotationStorage,
      linkService,
      xfaHtml: xfaPage
    });
    const viewport = XfaLayer.getPageViewport(xfaPage, {
      scale
    });
    builder.render({
      viewport,
      intent: "print"
    });
    page.append(builder.div);
  }
}

;// ./web/pdf_print_service.js


let activeService = null;
let dialog = null;
let overlayManager = null;
let viewerApp = {
  initialized: false
};
function renderPage(activeServiceOnEntry, pdfDocument, pageNumber, size, printResolution, optionalContentConfigPromise, printAnnotationStoragePromise) {
  const scratchCanvas = activeService.scratchCanvas;
  const PRINT_UNITS = printResolution / PixelsPerInch.PDF;
  scratchCanvas.width = Math.floor(size.width * PRINT_UNITS);
  scratchCanvas.height = Math.floor(size.height * PRINT_UNITS);
  const ctx = scratchCanvas.getContext("2d");
  ctx.save();
  ctx.fillStyle = "rgb(255, 255, 255)";
  ctx.fillRect(0, 0, scratchCanvas.width, scratchCanvas.height);
  ctx.restore();
  return Promise.all([pdfDocument.getPage(pageNumber), printAnnotationStoragePromise]).then(function ([pdfPage, printAnnotationStorage]) {
    const renderContext = {
      canvas: scratchCanvas,
      transform: [PRINT_UNITS, 0, 0, PRINT_UNITS, 0, 0],
      viewport: pdfPage.getViewport({
        scale: 1,
        rotation: size.rotation
      }),
      intent: "print",
      annotationMode: AnnotationMode.ENABLE_STORAGE,
      optionalContentConfigPromise,
      printAnnotationStorage
    };
    const renderTask = pdfPage.render(renderContext);
    return renderTask.promise.catch(reason => {
      if (!(reason instanceof RenderingCancelledException)) {
        console.error(reason);
      }
      throw reason;
    });
  });
}
class PDFPrintService {
  constructor({
    pdfDocument,
    pagesOverview,
    printContainer,
    printResolution,
    printAnnotationStoragePromise = null
  }) {
    this.pdfDocument = pdfDocument;
    this.pagesOverview = pagesOverview;
    this.printContainer = printContainer;
    this._printResolution = printResolution || 150;
    this._optionalContentConfigPromise = pdfDocument.getOptionalContentConfig({
      intent: "print"
    });
    this._printAnnotationStoragePromise = printAnnotationStoragePromise || Promise.resolve();
    this.currentPage = -1;
    this.scratchCanvas = document.createElement("canvas");
  }
  layout() {
    this.throwIfInactive();
    const body = document.querySelector("body");
    body.setAttribute("data-pdfjsprinting", true);
    const {
      width,
      height
    } = this.pagesOverview[0];
    const hasEqualPageSizes = this.pagesOverview.every(size => size.width === width && size.height === height);
    if (!hasEqualPageSizes) {
      console.warn("Not all pages have the same size. The printed result may be incorrect!");
    }
    this.pageStyleSheet = new CSSStyleSheet();
    this.pageStyleSheet.replaceSync(`@page { size: ${width}pt ${height}pt;}`);
    document.adoptedStyleSheets.push(this.pageStyleSheet);
  }
  destroy() {
    if (activeService !== this) {
      return;
    }
    this.printContainer.textContent = "";
    const body = document.querySelector("body");
    body.removeAttribute("data-pdfjsprinting");
    if (this.pageStyleSheet) {
      document.adoptedStyleSheets = document.adoptedStyleSheets.filter(styleSheet => styleSheet !== this.pageStyleSheet);
      this.pageStyleSheet = null;
    }
    if (this._blobURLs) {
      for (const url of this._blobURLs) {
        URL.revokeObjectURL(url);
      }
      this._blobURLs = null;
    }
    this.scratchCanvas.width = this.scratchCanvas.height = 0;
    this.scratchCanvas = null;
    activeService = null;
    ensureOverlay().then(function () {
      overlayManager.closeIfActive(dialog);
    });
  }
  renderPages() {
    if (this.pdfDocument.isPureXfa) {
      getXfaHtmlForPrinting(this.printContainer, this.pdfDocument);
      return Promise.resolve();
    }
    const pageCount = this.pagesOverview.length;
    const renderNextPage = (resolve, reject) => {
      this.throwIfInactive();
      if (++this.currentPage >= pageCount) {
        renderProgress(pageCount, pageCount);
        resolve();
        return;
      }
      const index = this.currentPage;
      renderProgress(index, pageCount);
      renderPage(this, this.pdfDocument, index + 1, this.pagesOverview[index], this._printResolution, this._optionalContentConfigPromise, this._printAnnotationStoragePromise).then(this.useRenderedPage.bind(this)).then(function () {
        renderNextPage(resolve, reject);
      }, reject);
    };
    return new Promise(renderNextPage);
  }
  useRenderedPage() {
    this.throwIfInactive();
    const img = document.createElement("img");
    this.scratchCanvas.toBlob(blob => {
      const blobURL = URL.createObjectURL(blob);
      img.src = blobURL;
      (this._blobURLs ??= []).push(blobURL);
    });
    const wrapper = document.createElement("div");
    wrapper.className = "printedPage";
    wrapper.append(img);
    this.printContainer.append(wrapper);
    const {
      promise,
      resolve,
      reject
    } = Promise.withResolvers();
    img.onload = resolve;
    img.onerror = reject;
    promise.catch(() => {});
    return promise;
  }
  performPrint() {
    this.throwIfInactive();
    return new Promise(resolve => {
      setTimeout(() => {
        if (!this.active) {
          resolve();
          return;
        }
        print.call(window);
        setTimeout(resolve, 20);
      }, 0);
    });
  }
  get active() {
    return this === activeService;
  }
  throwIfInactive() {
    if (!this.active) {
      throw new Error("This print request was cancelled or completed.");
    }
  }
}
const print = window.print;
window.print = function () {
  if (activeService) {
    console.warn("Ignored window.print() because of a pending print job.");
    return;
  }
  ensureOverlay().then(function () {
    if (activeService) {
      overlayManager.open(dialog);
    }
  });
  try {
    dispatchEvent("beforeprint");
  } finally {
    if (!activeService) {
      console.error("Expected print service to be initialized.");
      ensureOverlay().then(function () {
        overlayManager.closeIfActive(dialog);
      });
    } else {
      const activeServiceOnEntry = activeService;
      activeService.renderPages().then(() => activeServiceOnEntry.performPrint()).catch(() => {}).then(() => {
        if (activeServiceOnEntry.active) {
          abort();
        }
      });
    }
  }
};
function dispatchEvent(eventType) {
  const event = new CustomEvent(eventType, {
    bubbles: false,
    cancelable: false,
    detail: "custom"
  });
  window.dispatchEvent(event);
}
function abort() {
  if (activeService) {
    activeService.destroy();
    dispatchEvent("afterprint");
  }
}
function renderProgress(index, total) {
  dialog ||= document.getElementById("printServiceDialog");
  const progress = Math.round(100 * index / total);
  const progressBar = dialog.querySelector("progress");
  const progressPerc = dialog.querySelector(".relative-progress");
  progressBar.value = progress;
  progressPerc.setAttribute("data-l10n-args", JSON.stringify({
    progress
  }));
}
window.addEventListener("keydown", function (event) {
  if (event.keyCode === 80 && (event.ctrlKey || event.metaKey) && !event.altKey && (!event.shiftKey || window.chrome || window.opera)) {
    window.print();
    event.preventDefault();
    event.stopImmediatePropagation();
  }
}, true);
if ("onbeforeprint" in window) {
  const stopPropagationIfNeeded = function (event) {
    if (event.detail !== "custom") {
      event.stopImmediatePropagation();
    }
  };
  window.addEventListener("beforeprint", stopPropagationIfNeeded);
  window.addEventListener("afterprint", stopPropagationIfNeeded);
}
let overlayPromise;
function ensureOverlay() {
  if (!overlayPromise) {
    overlayManager = viewerApp.overlayManager;
    if (!overlayManager) {
      throw new Error("The overlay manager has not yet been initialized.");
    }
    dialog ||= document.getElementById("printServiceDialog");
    overlayPromise = overlayManager.register(dialog, true);
    document.getElementById("printCancel").onclick = abort;
    dialog.addEventListener("close", abort);
  }
  return overlayPromise;
}
class PDFPrintServiceFactory extends BasePrintServiceFactory {
  static initGlobals(app) {
    viewerApp = app;
  }
  static get supportsPrinting() {
    return shadow(this, "supportsPrinting", true);
  }
  static createPrintService(params) {
    if (activeService) {
      throw new Error("The print service is created and active.");
    }
    return activeService = new PDFPrintService(params);
  }
}

;// ./web/renderable_view.js
const RenderingStates = {
  INITIAL: 0,
  RUNNING: 1,
  PAUSED: 2,
  FINISHED: 3
};
class RenderableView {
  renderingId = "";
  renderTask = null;
  resume = null;
  get renderingState() {
    throw new Error("Abstract getter `renderingState` accessed");
  }
  set renderingState(state) {
    throw new Error("Abstract setter `renderingState` accessed");
  }
  async draw() {
    throw new Error("Not implemented: draw");
  }
}

;// ./web/pdf_rendering_queue.js


const CLEANUP_TIMEOUT = 30000;
class PDFRenderingQueue {
  #highestPriorityPage = null;
  #idleTimeout = null;
  #pdfThumbnailViewer = null;
  #pdfViewer = null;
  isThumbnailViewEnabled = false;
  onIdle = null;
  printing = false;
  constructor() {
    Object.defineProperty(this, "hasViewer", {
      value: () => !!this.#pdfViewer
    });
  }
  setViewer(pdfViewer) {
    this.#pdfViewer = pdfViewer;
  }
  setThumbnailViewer(pdfThumbnailViewer) {
    this.#pdfThumbnailViewer = pdfThumbnailViewer;
  }
  isHighestPriority(view) {
    return this.#highestPriorityPage === view.renderingId;
  }
  renderHighestPriority(currentlyVisiblePages) {
    if (this.#idleTimeout) {
      clearTimeout(this.#idleTimeout);
      this.#idleTimeout = null;
    }
    if (this.#pdfViewer.forceRendering(currentlyVisiblePages)) {
      return;
    }
    if (this.isThumbnailViewEnabled && this.#pdfThumbnailViewer?.forceRendering()) {
      return;
    }
    if (this.printing) {
      return;
    }
    if (this.onIdle) {
      this.#idleTimeout = setTimeout(this.onIdle.bind(this), CLEANUP_TIMEOUT);
    }
  }
  getHighestPriority(visible, views, scrolledDown, preRenderExtra = false, ignoreDetailViews = false) {
    const visibleViews = visible.views,
      numVisible = visibleViews.length;
    if (numVisible === 0) {
      return null;
    }
    for (let i = 0; i < numVisible; i++) {
      const view = visibleViews[i].view;
      if (!this.isViewFinished(view)) {
        return view;
      }
    }
    if (!ignoreDetailViews) {
      for (let i = 0; i < numVisible; i++) {
        const {
          detailView
        } = visibleViews[i].view;
        if (detailView && !this.isViewFinished(detailView)) {
          return detailView;
        }
      }
    }
    const firstId = visible.first.id,
      lastId = visible.last.id;
    if (lastId - firstId + 1 > numVisible) {
      const visibleIds = visible.ids;
      for (let i = 1, ii = lastId - firstId; i < ii; i++) {
        const holeId = scrolledDown ? firstId + i : lastId - i;
        if (visibleIds.has(holeId)) {
          continue;
        }
        const holeView = views[holeId - 1];
        if (!this.isViewFinished(holeView)) {
          return holeView;
        }
      }
    }
    let preRenderIndex = scrolledDown ? lastId : firstId - 2;
    let preRenderView = views[preRenderIndex];
    if (preRenderView && !this.isViewFinished(preRenderView)) {
      return preRenderView;
    }
    if (preRenderExtra) {
      preRenderIndex += scrolledDown ? 1 : -1;
      preRenderView = views[preRenderIndex];
      if (preRenderView && !this.isViewFinished(preRenderView)) {
        return preRenderView;
      }
    }
    return null;
  }
  isViewFinished(view) {
    return view.renderingState === RenderingStates.FINISHED;
  }
  renderView(view) {
    switch (view.renderingState) {
      case RenderingStates.FINISHED:
        return false;
      case RenderingStates.PAUSED:
        this.#highestPriorityPage = view.renderingId;
        view.resume();
        break;
      case RenderingStates.RUNNING:
        this.#highestPriorityPage = view.renderingId;
        break;
      case RenderingStates.INITIAL:
        this.#highestPriorityPage = view.renderingId;
        view.draw().finally(() => {
          this.renderHighestPriority();
        }).catch(reason => {
          if (reason instanceof RenderingCancelledException) {
            return;
          }
          console.error("renderView:", reason);
        });
        break;
    }
    return true;
  }
}

;// ./web/pdf_scripting_manager.js




class PDFScriptingManager {
  #closeCapability = null;
  #destroyCapability = null;
  #docProperties = null;
  #eventAC = null;
  #eventBus = null;
  #externalServices = null;
  #objectIds = null;
  #pdfDocument = null;
  #pdfViewer = null;
  #ready = false;
  #sandboxCreated = false;
  #scripting = null;
  #pendingDocEvents = new Map();
  constructor({
    eventBus,
    externalServices = null,
    docProperties = null
  }) {
    this.#eventBus = eventBus;
    this.#externalServices = externalServices;
    this.#docProperties = docProperties;
  }
  setViewer(pdfViewer) {
    this.#pdfViewer = pdfViewer;
  }
  async setDocument(pdfDocument) {
    if (this.#pdfDocument) {
      await this.#destroyScripting();
    }
    this.#pdfDocument = pdfDocument;
    if (!pdfDocument) {
      return;
    }
    const [objects, calculationOrder, docActions] = await Promise.all([pdfDocument.getFieldObjects(), pdfDocument.getCalculationOrderIds(), pdfDocument.getJSActions()]);
    if (!objects && !docActions) {
      await this.#destroyScripting();
      return;
    }
    if (pdfDocument !== this.#pdfDocument) {
      return;
    }
    if (objects) {
      this.#objectIds = new Set();
      for (const fields of objects.values()) {
        for (const {
          id
        } of fields) {
          this.#objectIds.add(id);
        }
      }
    }
    try {
      this.#scripting = this.#initScripting();
    } catch (error) {
      console.error("setDocument:", error);
      await this.#destroyScripting();
      return;
    }
    const eventBus = this.#eventBus;
    this.#eventAC = new AbortController();
    const evtOpts = {
      signal: this.#eventAC.signal,
      ...internalOpt
    };
    eventBus.on("updatefromsandbox", event => {
      if (event?.source === window) {
        this.#updateFromSandbox(event.detail);
      }
    }, evtOpts);
    eventBus.on("dispatcheventinsandbox", event => {
      this.#scripting?.dispatchEventInSandbox(event.detail);
    }, evtOpts);
    eventBus.on("pagechanging", ({
      pageNumber,
      previous
    }) => {
      if (pageNumber === previous) {
        return;
      }
      this.#dispatchPageClose(previous);
      this.#dispatchPageOpen(pageNumber);
    }, evtOpts);
    eventBus.on("pagerendered", ({
      pageNumber
    }) => {
      if (!this._pageOpenPending.has(pageNumber)) {
        return;
      }
      if (pageNumber !== this.#pdfViewer.currentPageNumber) {
        return;
      }
      this.#dispatchPageOpen(pageNumber);
    }, evtOpts);
    eventBus.on("pagesdestroy", async () => {
      await this.#dispatchPageClose(this.#pdfViewer.currentPageNumber);
      await this.#scripting?.dispatchEventInSandbox({
        id: "doc",
        name: "WillClose"
      });
      this.#closeCapability?.resolve();
    }, evtOpts);
    try {
      const docProperties = await this.#docProperties(pdfDocument);
      if (pdfDocument !== this.#pdfDocument) {
        return;
      }
      await this.#scripting.createSandbox({
        objects,
        calculationOrder,
        appInfo: {
          platform: navigator.platform,
          language: navigator.language
        },
        docInfo: {
          ...docProperties,
          actions: docActions
        }
      });
      if (pdfDocument === this.#pdfDocument) {
        this.#sandboxCreated = true;
      }
      eventBus.dispatch("sandboxcreated", {
        source: this
      });
    } catch (error) {
      console.error("setDocument:", error);
      await this.#destroyScripting();
      return;
    }
    await this.#scripting?.dispatchEventInSandbox({
      id: "doc",
      name: "Open"
    });
    await this.#dispatchPageOpen(this.#pdfViewer.currentPageNumber, true);
    Promise.resolve().then(() => {
      if (pdfDocument === this.#pdfDocument) {
        this.#ready = true;
      }
    });
  }
  async dispatchWillSave() {
    return this.#dispatchDocEventAndWait("WillSave");
  }
  async dispatchDidSave() {
    return this.#scripting?.dispatchEventInSandbox({
      id: "doc",
      name: "DidSave"
    });
  }
  async dispatchWillPrint() {
    return this.#dispatchDocEventAndWait("WillPrint");
  }
  async #dispatchDocEventAndWait(name) {
    if (!this.#scripting || !this.#sandboxCreated) {
      return;
    }
    const capability = Promise.withResolvers();
    const pendingEvents = this.#pendingDocEvents.getOrInsertComputed(name, makeArr);
    pendingEvents.push(capability);
    try {
      await this.#scripting.dispatchEventInSandbox({
        id: "doc",
        name
      });
    } catch (ex) {
      const index = pendingEvents.indexOf(capability);
      if (index >= 0) {
        pendingEvents.splice(index, 1);
      }
      throw ex;
    }
    await capability.promise;
  }
  async dispatchDidPrint() {
    return this.#scripting?.dispatchEventInSandbox({
      id: "doc",
      name: "DidPrint"
    });
  }
  get destroyPromise() {
    return this.#destroyCapability?.promise || null;
  }
  get ready() {
    return this.#ready;
  }
  get _pageOpenPending() {
    return shadow(this, "_pageOpenPending", new Set());
  }
  get _visitedPages() {
    return shadow(this, "_visitedPages", new Map());
  }
  async #updateFromSandbox(detail) {
    const pdfViewer = this.#pdfViewer;
    const isInPresentationMode = pdfViewer.isInPresentationMode || pdfViewer.isChangingPresentationMode;
    const {
      id,
      siblings,
      command,
      value
    } = detail;
    if (!id) {
      switch (command) {
        case "clear":
          console.clear();
          break;
        case "error":
          console.error(value);
          break;
        case "layout":
          if (!isInPresentationMode) {
            const modes = apiPageLayoutToViewerModes(value);
            pdfViewer.spreadMode = modes.spreadMode;
          }
          break;
        case "page-num":
          pdfViewer.currentPageNumber = value + 1;
          break;
        case "print":
          await pdfViewer.pagesPromise;
          this.#eventBus.dispatch("print", {
            source: this
          });
          break;
        case "println":
          console.log(value);
          break;
        case "zoom":
          if (!isInPresentationMode) {
            pdfViewer.currentScaleValue = value;
          }
          break;
        case "SaveAs":
          this.#eventBus.dispatch("download", {
            source: this
          });
          break;
        case "FirstPage":
          pdfViewer.currentPageNumber = 1;
          break;
        case "LastPage":
          pdfViewer.currentPageNumber = pdfViewer.pagesCount;
          break;
        case "NextPage":
          pdfViewer.nextPage();
          break;
        case "PrevPage":
          pdfViewer.previousPage();
          break;
        case "ZoomViewIn":
          if (!isInPresentationMode) {
            pdfViewer.increaseScale();
          }
          break;
        case "ZoomViewOut":
          if (!isInPresentationMode) {
            pdfViewer.decreaseScale();
          }
          break;
        case "WillPrintFinished":
        case "WillSaveFinished":
          {
            const name = command.slice(0, -"Finished".length);
            this.#pendingDocEvents.get(name)?.shift()?.resolve();
            break;
          }
      }
      return;
    }
    if (isInPresentationMode && detail.focus) {
      return;
    }
    delete detail.id;
    delete detail.siblings;
    const ids = siblings ? [id, ...siblings] : [id];
    for (const elementId of ids) {
      if (!this.#objectIds?.has(elementId)) {
        continue;
      }
      const element = document.querySelector(`[data-element-id="${elementId}"]`);
      if (element) {
        element.dispatchEvent(new CustomEvent("updatefromsandbox", {
          detail
        }));
      } else {
        this.#pdfDocument?.annotationStorage.setValue(elementId, detail);
      }
    }
  }
  async #dispatchPageOpen(pageNumber, initialize = false) {
    const pdfDocument = this.#pdfDocument,
      visitedPages = this._visitedPages;
    if (initialize) {
      this.#closeCapability = Promise.withResolvers();
    }
    if (!this.#closeCapability) {
      return;
    }
    const pageView = this.#pdfViewer.getPageView(pageNumber - 1);
    if (pageView?.renderingState !== RenderingStates.FINISHED) {
      this._pageOpenPending.add(pageNumber);
      return;
    }
    this._pageOpenPending.delete(pageNumber);
    const actionsPromise = (async () => {
      const actions = await (!visitedPages.has(pageNumber) ? pageView.pdfPage?.getJSActions() : null);
      if (pdfDocument !== this.#pdfDocument) {
        return;
      }
      await this.#scripting?.dispatchEventInSandbox({
        id: "page",
        name: "PageOpen",
        pageNumber,
        actions
      });
    })();
    visitedPages.set(pageNumber, actionsPromise);
  }
  async #dispatchPageClose(pageNumber) {
    const pdfDocument = this.#pdfDocument,
      visitedPages = this._visitedPages;
    if (!this.#closeCapability) {
      return;
    }
    if (this._pageOpenPending.has(pageNumber)) {
      return;
    }
    const actionsPromise = visitedPages.get(pageNumber);
    if (!actionsPromise) {
      return;
    }
    visitedPages.set(pageNumber, null);
    await actionsPromise;
    if (pdfDocument !== this.#pdfDocument) {
      return;
    }
    await this.#scripting?.dispatchEventInSandbox({
      id: "page",
      name: "PageClose",
      pageNumber
    });
  }
  #initScripting() {
    this.#destroyCapability = Promise.withResolvers();
    if (this.#scripting) {
      throw new Error("#initScripting: Scripting already exists.");
    }
    return this.#externalServices.createScripting();
  }
  async #destroyScripting() {
    this.#objectIds = null;
    this.#sandboxCreated = false;
    if (!this.#scripting) {
      this.#pdfDocument = null;
      this.#destroyCapability?.resolve();
      return;
    }
    if (this.#closeCapability) {
      await Promise.race([this.#closeCapability.promise, new Promise(resolve => {
        setTimeout(resolve, 1000);
      })]).catch(() => {});
      this.#closeCapability = null;
    }
    this.#pdfDocument = null;
    try {
      await this.#scripting.destroySandbox();
    } catch {}
    for (const pendingEvents of this.#pendingDocEvents.values()) {
      for (const capability of pendingEvents) {
        capability.reject(new Error("Scripting destroyed."));
      }
    }
    this.#pendingDocEvents.clear();
    this.#eventAC?.abort();
    this.#eventAC = null;
    this._pageOpenPending.clear();
    this._visitedPages.clear();
    this.#scripting = null;
    this.#ready = false;
    this.#destroyCapability?.resolve();
  }
}

;// ./web/pdf_text_extractor.js
/* unused harmony import specifier */ var pdf_text_extractor_internalOpt;

class PdfTextExtractor {
  #externalServices;
  #textPromise;
  #capability = Promise.withResolvers();
  constructor(externalServices, pdfViewer, eventBus) {
    this.#externalServices = externalServices;
    eventBus.on("pagesinit", () => {
      this.#capability.resolve(pdfViewer);
    }, pdf_text_extractor_internalOpt);
    eventBus.on("pagesdestroy", () => {
      this.#capability.reject(new Error("pagesdestroy"));
      this.#textPromise = null;
      this.#capability = Promise.withResolvers();
    }, pdf_text_extractor_internalOpt);
    window.addEventListener("requestTextContent", ({
      detail
    }) => {
      this.extractTextContent(detail.requestId);
    });
  }
  async extractTextContent(requestId) {
    if (!this.#textPromise) {
      const textPromise = this.#textPromise = this.#capability.promise.then(pdfViewer => pdfViewer.getAllText());
      textPromise.then(() => {
        setTimeout(() => {
          if (this.#textPromise === textPromise) {
            this.#textPromise = null;
          }
        }, 5000);
      });
    }
    this.#externalServices.reportText({
      text: await this.#textPromise,
      requestId
    });
  }
}

;// ./web/menu.js

class Menu {
  #triggeringButton;
  #menu;
  #menuItems;
  #openMenuAC = null;
  #menuAC = new AbortController();
  #lastIndex = -1;
  #onFocusOutBound = this.#onFocusOut.bind(this);
  constructor(menuContainer, triggeringButton, menuItems) {
    this.#menu = menuContainer;
    this.#triggeringButton = triggeringButton;
    this.#menuItems = Array.isArray(menuItems) ? menuItems : [...this.#menu.querySelectorAll("button")];
    this.#setUpMenu();
  }
  #closeMenu() {
    if (!this.#openMenuAC) {
      return;
    }
    const menu = this.#menu;
    this.#triggeringButton.ariaExpanded = "false";
    this.#openMenuAC.abort();
    this.#openMenuAC = null;
    if (menu.contains(document.activeElement)) {
      setTimeout(() => {
        if (!menu.contains(document.activeElement)) {
          this.#triggeringButton.focus();
        }
      }, 0);
    }
    this.#lastIndex = -1;
  }
  #openMenu() {
    if (this.#openMenuAC) {
      return;
    }
    const menu = this.#menu;
    this.#triggeringButton.ariaExpanded = "true";
    this.#openMenuAC = new AbortController();
    const signal = AbortSignal.any([this.#menuAC.signal, this.#openMenuAC.signal]);
    window.addEventListener("pointerdown", ({
      target
    }) => {
      if (!this.#triggeringButton.contains(target) && !menu.contains(target)) {
        this.#closeMenu();
      }
    }, {
      signal
    });
    const closeMenu = this.#closeMenu.bind(this);
    window.addEventListener("blur", closeMenu, {
      signal
    });
    menu.addEventListener("focusout", this.#onFocusOutBound, {
      signal
    });
  }
  #onFocusOut({
    relatedTarget
  }) {
    if (!this.#triggeringButton.contains(relatedTarget) && !this.#menu.contains(relatedTarget)) {
      this.#closeMenu();
    }
  }
  #setUpMenu() {
    this.#triggeringButton.addEventListener("click", e => {
      if (this.#openMenuAC) {
        this.#closeMenu();
        return;
      }
      this.#openMenu();
    });
    this.#triggeringButton.addEventListener("focusout", this.#onFocusOutBound);
    const {
      signal
    } = this.#menuAC;
    this.#menu.addEventListener("keydown", e => {
      switch (e.key) {
        case "Escape":
          this.#closeMenu();
          stopEvent(e);
          break;
        case "ArrowDown":
          this.#goToNextItem(e.target, true);
          stopEvent(e);
          break;
        case "ArrowUp":
          this.#goToNextItem(e.target, false);
          stopEvent(e);
          break;
        case "Home":
          this.#goToFirstLast(false);
          stopEvent(e);
          break;
        case "End":
          this.#goToFirstLast(true);
          stopEvent(e);
          break;
        default:
          const {
            key
          } = e;
          if (!/^\p{L}$/u.test(key)) {
            break;
          }
          const char = key.toLocaleLowerCase();
          this.#goToNextItem(e.target, true, item => item.textContent.trim().toLowerCase().startsWith(char));
          stopEvent(e);
          break;
      }
    }, {
      signal,
      capture: true
    });
    this.#menu.addEventListener("contextmenu", noContextMenu, {
      signal
    });
    this.#menu.addEventListener("click", this.#closeMenu.bind(this), {
      signal,
      capture: true
    });
    this.#triggeringButton.addEventListener("keydown", e => {
      switch (e.key) {
        case " ":
        case "Enter":
        case "ArrowDown":
        case "Home":
          stopEvent(e);
          if (!this.#openMenuAC) {
            this.#openMenu();
          }
          this.#goToFirstLast(false);
          break;
        case "ArrowUp":
        case "End":
          stopEvent(e);
          if (!this.#openMenuAC) {
            this.#openMenu();
          }
          this.#goToFirstLast(true);
          break;
        case "Escape":
          this.#closeMenu();
          stopEvent(e);
          break;
      }
    }, {
      signal
    });
  }
  #goToNextItem(element, forward, check = () => true) {
    const index = this.#lastIndex === -1 ? this.#menuItems.indexOf(element) : this.#lastIndex;
    const len = this.#menuItems.length;
    const increment = forward ? 1 : len - 1;
    for (let i = (index + increment) % len; i !== index; i = (i + increment) % len) {
      const menuItem = this.#menuItems[i];
      if (!menuItem.disabled && !menuItem.classList.contains("hidden") && check(menuItem)) {
        menuItem.focus();
        this.#lastIndex = i;
        break;
      }
    }
  }
  #goToFirstLast(last = false) {
    const i = this.#menuItems[last ? "findLastIndex" : "findIndex"](item => !item.disabled && !item.classList.contains("hidden"));
    if (i >= 0) {
      this.#menuItems[i].focus();
      this.#lastIndex = i;
    }
  }
  destroy() {
    this.#closeMenu();
    this.#menuAC?.abort();
    this.#menuAC = null;
  }
}

;// ./web/pdf_thumbnail_view.js



const DRAW_UPSCALE_FACTOR = 2;
const MAX_NUM_SCALING_STEPS = 3;
const THUMBNAIL_WIDTH = 126;
function getTempCanvas(width, height) {
  const canvas = new OffscreenCanvas(width, height);
  const ctx = canvas.getContext("2d", {
    alpha: false
  });
  ctx.save();
  ctx.fillStyle = "rgb(255, 255, 255)";
  ctx.fillRect(0, 0, width, height);
  ctx.restore();
  return [canvas, ctx];
}
class PDFThumbnailView extends RenderableView {
  #renderingState = RenderingStates.INITIAL;
  constructor({
    container,
    eventBus,
    id,
    defaultViewport,
    optionalContentConfigPromise,
    linkService,
    renderingQueue,
    maxCanvasPixels,
    maxCanvasDim,
    pageColors,
    enableSplitMerge = false
  }) {
    super();
    this.id = id;
    this.renderingId = `thumbnail${id}`;
    this.pageLabel = null;
    this.pdfPage = null;
    this.rotation = 0;
    this.viewport = defaultViewport;
    this.pdfPageRotate = defaultViewport.rotation;
    this._optionalContentConfigPromise = optionalContentConfigPromise || null;
    this.maxCanvasPixels = maxCanvasPixels ?? AppOptions.get("maxCanvasPixels");
    this.maxCanvasDim = maxCanvasDim || AppOptions.get("maxCanvasDim");
    this.pageColors = pageColors || null;
    this.eventBus = eventBus;
    this.linkService = linkService;
    this.renderingQueue = renderingQueue;
    this.placeholder = null;
    const thumbnailContainer = this.div = document.createElement("div");
    thumbnailContainer.className = "thumbnail";
    thumbnailContainer.setAttribute("page-number", id);
    const imageContainer = this.imageContainer = document.createElement("div");
    thumbnailContainer.append(imageContainer);
    imageContainer.classList.add("thumbnailImageContainer", "missingThumbnailImage");
    imageContainer.role = "button";
    imageContainer.tabIndex = -1;
    imageContainer.draggable = false;
    imageContainer.setAttribute("page-number", id);
    imageContainer.setAttribute("data-l10n-id", "pdfjs-thumb-page-title1");
    imageContainer.setAttribute("data-l10n-args", this.#getPageL10nArgs(true));
    const image = this.image = document.createElement("img");
    imageContainer.append(image);
    if (enableSplitMerge) {
      const checkbox = this.checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.tabIndex = -1;
      checkbox.setAttribute("data-l10n-id", "pdfjs-thumb-page-checkbox1");
      checkbox.setAttribute("data-l10n-args", this.#getPageL10nArgs());
      thumbnailContainer.append(checkbox);
      this.pasteButton = null;
    }
    this.#updateDims();
    container.append(thumbnailContainer);
  }
  clone(container, id) {
    const thumbnailView = new PDFThumbnailView({
      container,
      id,
      eventBus: this.eventBus,
      defaultViewport: this.viewport,
      optionalContentConfigPromise: this._optionalContentConfigPromise,
      linkService: this.linkService,
      renderingQueue: this.renderingQueue,
      maxCanvasPixels: this.maxCanvasPixels,
      maxCanvasDim: this.maxCanvasDim,
      pageColors: this.pageColors,
      enableSplitMerge: !!this.checkbox
    });
    const {
      imageContainer
    } = this;
    if (!imageContainer.classList.contains("missingThumbnailImage")) {
      thumbnailView.image.replaceWith(this.image.cloneNode(true));
      thumbnailView.imageContainer.classList.remove("missingThumbnailImage");
    }
    return thumbnailView;
  }
  addPasteButton(pasteCallback) {
    if (this.pasteButton) {
      return;
    }
    const pasteButton = this.pasteButton = document.createElement("button");
    pasteButton.classList.add("thumbnailPasteButton", "viewsManagerButton");
    pasteButton.tabIndex = 0;
    pasteButton.setAttribute("data-l10n-id", "pdfjs-views-manager-paste-button-after");
    pasteButton.setAttribute("data-l10n-args", this.#getPageL10nArgs());
    const span = document.createElement("span");
    span.setAttribute("data-l10n-id", "pdfjs-views-manager-paste-button-label");
    pasteButton.append(span);
    pasteButton.addEventListener("click", () => {
      pasteCallback(this.id);
    });
    if (this.id === 1) {
      const prevPasteButton = this.prevPasteButton = pasteButton.cloneNode(true);
      prevPasteButton.setAttribute("data-l10n-id", "pdfjs-views-manager-paste-button-before");
      prevPasteButton.addEventListener("click", () => {
        pasteCallback(0);
      });
      this.imageContainer.before(prevPasteButton);
    }
    this.imageContainer.after(pasteButton);
  }
  removePasteButton() {
    this.pasteButton?.remove();
    this.pasteButton = null;
    this.prevPasteButton?.remove();
    this.prevPasteButton = null;
  }
  toggleSelected(isSelected) {
    if (this.checkbox) {
      this.checkbox.checked = isSelected;
    }
  }
  updateId(newId) {
    this.id = newId;
    this.renderingId = `thumbnail${newId}`;
    this.div.setAttribute("page-number", newId);
    this.imageContainer.setAttribute("page-number", newId);
    this.setPageLabel(this.pageLabel);
  }
  #updateDims() {
    const {
      width,
      height
    } = this.viewport;
    const ratio = width / height;
    const canvasWidth = this.canvasWidth = THUMBNAIL_WIDTH;
    const canvasHeight = this.canvasHeight = canvasWidth / ratio | 0;
    this.scale = canvasWidth / width;
    this.imageContainer.style.height = `${canvasHeight}px`;
  }
  get renderingState() {
    return this.#renderingState;
  }
  set renderingState(state) {
    this.#renderingState = state;
  }
  setPdfPage(pdfPage) {
    this.pdfPage = pdfPage;
    this.pdfPageRotate = pdfPage.rotate;
    const totalRotation = (this.rotation + this.pdfPageRotate) % 360;
    this.viewport = pdfPage.getViewport({
      scale: 1,
      rotation: totalRotation
    });
    this.reset();
  }
  reset() {
    this.cancelRendering();
    this.renderingState = RenderingStates.INITIAL;
    this.#updateDims();
    const {
      image,
      imageContainer
    } = this;
    const url = image.src;
    if (url) {
      URL.revokeObjectURL(url);
      image.src = "";
      imageContainer.removeAttribute("data-l10n-id");
      imageContainer.removeAttribute("data-l10n-args");
      imageContainer.classList.add("missingThumbnailImage");
    }
  }
  destroy() {
    this.reset();
    this.toggleCurrent(false);
    this.div.remove();
  }
  update({
    rotation = null
  }) {
    if (typeof rotation === "number") {
      this.rotation = rotation;
    }
    const totalRotation = (this.rotation + this.pdfPageRotate) % 360;
    this.viewport = this.viewport.clone({
      scale: 1,
      rotation: totalRotation
    });
    this.reset();
  }
  toggleCurrent(isCurrent) {
    const {
      imageContainer
    } = this;
    if (isCurrent) {
      imageContainer.ariaCurrent = "page";
      imageContainer.tabIndex = 0;
      if (this.checkbox) {
        this.checkbox.tabIndex = 0;
      }
    } else {
      imageContainer.ariaCurrent = false;
      imageContainer.tabIndex = -1;
      if (this.checkbox) {
        this.checkbox.tabIndex = -1;
      }
    }
  }
  cancelRendering() {
    if (this.renderTask) {
      this.renderTask.cancel();
      this.renderTask = null;
    }
    this.resume = null;
  }
  #getPageDrawContext(upscaleFactor = 1) {
    const outputScale = new OutputScale();
    const width = upscaleFactor * this.canvasWidth,
      height = upscaleFactor * this.canvasHeight;
    outputScale.limitCanvas(width, height, this.maxCanvasPixels, this.maxCanvasDim);
    const canvas = document.createElement("canvas");
    canvas.width = width * outputScale.sx | 0;
    canvas.height = height * outputScale.sy | 0;
    const transform = outputScale.scaled ? [outputScale.sx, 0, 0, outputScale.sy, 0, 0] : null;
    return {
      canvas,
      transform
    };
  }
  async #convertCanvasToImage(canvas) {
    if (this.renderingState !== RenderingStates.FINISHED) {
      throw new Error("#convertCanvasToImage: Rendering has not finished.");
    }
    const reducedCanvas = this.#reduceImage(canvas);
    const {
      imageContainer,
      image
    } = this;
    const {
      promise,
      resolve
    } = Promise.withResolvers();
    reducedCanvas.toBlob(resolve);
    const blob = await promise;
    image.src = URL.createObjectURL(blob);
    image.setAttribute("data-l10n-id", "pdfjs-thumb-page-canvas");
    image.setAttribute("data-l10n-args", this.#getPageL10nArgs());
    imageContainer.classList.remove("missingThumbnailImage");
  }
  async draw() {
    if (this.renderingState !== RenderingStates.INITIAL) {
      console.error("Must be in new state before drawing");
      return;
    }
    const {
      pageColors,
      pdfPage
    } = this;
    if (!pdfPage) {
      this.renderingState = RenderingStates.FINISHED;
      throw new Error("pdfPage is not loaded");
    }
    this.renderingState = RenderingStates.RUNNING;
    const {
      canvas,
      transform
    } = this.#getPageDrawContext(DRAW_UPSCALE_FACTOR);
    const drawViewport = this.viewport.clone({
      scale: DRAW_UPSCALE_FACTOR * this.scale
    });
    const renderContinueCallback = cont => {
      if (!this.renderingQueue.isHighestPriority(this)) {
        this.renderingState = RenderingStates.PAUSED;
        this.resume = () => {
          this.renderingState = RenderingStates.RUNNING;
          cont();
        };
        return;
      }
      cont();
    };
    const renderContext = {
      canvas,
      transform,
      viewport: drawViewport,
      optionalContentConfigPromise: this._optionalContentConfigPromise,
      pageColors
    };
    const renderTask = this.renderTask = pdfPage.render(renderContext);
    renderTask.onContinue = renderContinueCallback;
    let error = null;
    try {
      await renderTask.promise;
    } catch (e) {
      if (e instanceof RenderingCancelledException) {
        return;
      }
      error = e;
    } finally {
      if (renderTask === this.renderTask) {
        this.renderTask = null;
      }
    }
    this.renderingState = RenderingStates.FINISHED;
    await this.#convertCanvasToImage(canvas);
    this.eventBus.dispatch("thumbnailrendered", {
      source: this,
      pageNumber: this.id,
      pdfPage
    });
    if (error) {
      throw error;
    }
  }
  setImage(pageView) {
    if (this.renderingState !== RenderingStates.INITIAL) {
      return;
    }
    const {
      thumbnailCanvas: canvas,
      pdfPage,
      scale
    } = pageView;
    if (!canvas) {
      return;
    }
    if (!this.pdfPage) {
      this.setPdfPage(pdfPage);
    }
    if (scale < this.scale) {
      return;
    }
    this.renderingState = RenderingStates.FINISHED;
    this.#convertCanvasToImage(canvas);
  }
  #getReducedImageDims(canvas) {
    const width = canvas.width << MAX_NUM_SCALING_STEPS,
      height = canvas.height << MAX_NUM_SCALING_STEPS;
    const outputScale = new OutputScale();
    outputScale.sx = outputScale.sy = 1;
    outputScale.limitCanvas(width, height, this.maxCanvasPixels, this.maxCanvasDim);
    return [width * outputScale.sx | 0, height * outputScale.sy | 0];
  }
  #reduceImage(img) {
    const {
      canvas
    } = this.#getPageDrawContext(1);
    const ctx = canvas.getContext("2d", {
      alpha: false,
      willReadFrequently: false
    });
    if (img.width <= 2 * canvas.width) {
      ctx.drawImage(img, 0, 0, img.width, img.height, 0, 0, canvas.width, canvas.height);
      return canvas;
    }
    let [reducedWidth, reducedHeight] = this.#getReducedImageDims(canvas);
    const [reducedImage, reducedImageCtx] = getTempCanvas(reducedWidth, reducedHeight);
    while (reducedWidth > img.width || reducedHeight > img.height) {
      reducedWidth >>= 1;
      reducedHeight >>= 1;
    }
    reducedImageCtx.drawImage(img, 0, 0, img.width, img.height, 0, 0, reducedWidth, reducedHeight);
    while (reducedWidth > 2 * canvas.width) {
      reducedImageCtx.drawImage(reducedImage, 0, 0, reducedWidth, reducedHeight, 0, 0, reducedWidth >> 1, reducedHeight >> 1);
      reducedWidth >>= 1;
      reducedHeight >>= 1;
    }
    ctx.drawImage(reducedImage, 0, 0, reducedWidth, reducedHeight, 0, 0, canvas.width, canvas.height);
    return canvas;
  }
  #getPageL10nArgs(hasTotal = false) {
    return JSON.stringify({
      page: this.pageLabel ?? this.id,
      total: hasTotal ? this.linkService.pagesCount : undefined
    });
  }
  setPageLabel(label) {
    this.pageLabel = typeof label === "string" ? label : null;
    this.imageContainer.setAttribute("data-l10n-args", this.#getPageL10nArgs(true));
    this.image.setAttribute("data-l10n-args", this.#getPageL10nArgs());
    this.checkbox?.setAttribute("data-l10n-args", this.#getPageL10nArgs());
  }
}

;// ./web/pdf_thumbnail_viewer.js






const SCROLL_OPTIONS = {
  behavior: "instant",
  block: "nearest",
  inline: "nearest",
  container: "nearest"
};
const DRAG_THRESHOLD_IN_PIXELS = 5;
const PIXELS_TO_SCROLL_WHEN_DRAGGING = 20;
const SPACE_FOR_DRAG_MARKER_WHEN_NO_NEXT_ELEMENT = 15;
class PDFThumbnailViewer {
  static #draggingScaleFactor = 0;
  #enableMerge = false;
  #enableSplitMerge = false;
  #dragAC = null;
  #abortSignal = undefined;
  #externalDragActive = false;
  #draggedContainer = null;
  #thumbnailsPositions = null;
  #lastDraggedOverIndex = NaN;
  #selectedPages = null;
  #draggedImageX = 0;
  #draggedImageY = 0;
  #draggedImageWidth = 0;
  #draggedImageHeight = 0;
  #draggedImageOffsetX = 0;
  #draggedImageOffsetY = 0;
  #dragMarker = null;
  #pageNumberToRemove = NaN;
  #currentScrollBottom = 0;
  #currentScrollTop = 0;
  #pagesMapper = null;
  #manageExportButton = null;
  #manageDeleteButton = null;
  #manageCopyButton = null;
  #manageCutButton = null;
  #copiedThumbnails = null;
  #savedThumbnails = null;
  #deletedPageNumbers = null;
  #copiedPageNumbers = null;
  #boundPastePages = this.#pastePages.bind(this);
  #isCut = false;
  #isOneColumnView = false;
  #scrollableContainerWidth = 0;
  #scrollableContainerHeight = 0;
  #statusLabel = null;
  #statusBar = null;
  #deselectButton = null;
  #undoBar = null;
  #undoLabel = null;
  #undoButton = null;
  #undoCloseButton = null;
  #waitingBar = null;
  #isInPasteMode = false;
  #hasUndoBarVisible = false;
  #newBadge = null;
  #l10n = null;
  #toggleBarId = 0;
  constructor({
    container,
    eventBus,
    linkService,
    renderingQueue,
    l10n,
    maxCanvasPixels,
    maxCanvasDim,
    pageColors,
    abortSignal,
    enableMerge,
    enableSplitMerge,
    enableNewBadge,
    statusBar,
    undoBar,
    waitingBar,
    manageMenu,
    addFileComponent
  }) {
    this.scrollableContainer = container.parentElement;
    this.container = container;
    this.eventBus = eventBus;
    this.linkService = linkService;
    this.renderingQueue = renderingQueue;
    this.#l10n = l10n;
    this.maxCanvasPixels = maxCanvasPixels;
    this.maxCanvasDim = maxCanvasDim;
    this.pageColors = pageColors || null;
    this.#abortSignal = abortSignal;
    this.#enableMerge = enableMerge || false;
    this.#enableSplitMerge = enableSplitMerge || false;
    this.#statusLabel = statusBar?.viewsManagerStatusActionLabel || null;
    this.#deselectButton = statusBar?.viewsManagerStatusActionDeselectButton || null;
    this.#statusBar = statusBar?.viewsManagerStatusAction || null;
    this.#undoBar = undoBar?.viewsManagerStatusUndo || null;
    this.#undoLabel = undoBar?.viewsManagerStatusUndoLabel || null;
    this.#undoButton = undoBar?.viewsManagerStatusUndoButton || null;
    this.#undoCloseButton = undoBar?.viewsManagerStatusUndoCloseButton || null;
    this.#waitingBar = waitingBar || null;
    if (this.#enableSplitMerge && manageMenu) {
      const {
        button: menuButton,
        menu,
        copy,
        cut,
        delete: del,
        exportSelected
      } = manageMenu;
      if (enableNewBadge) {
        const newSpan = document.createElement("span");
        newSpan.setAttribute("data-l10n-id", "pdfjs-new-badge-content");
        newSpan.classList.add("newBadge");
        menuButton.parentElement.before(newSpan);
        this.#newBadge = newSpan;
      }
      eventBus.on("pagesloaded", () => {
        menuButton.disabled = false;
      }, {
        once: true,
        ...internalOpt
      });
      this._manageMenu = new Menu(menu, menuButton, [copy, cut, del, exportSelected]);
      this.#manageExportButton = exportSelected;
      exportSelected.addEventListener("click", this.#saveExtractedPages.bind(this));
      this.#manageDeleteButton = del;
      del.addEventListener("click", this.#deletePages.bind(this, "delete"));
      this.#manageCopyButton = copy;
      copy.addEventListener("click", this.#copyPages.bind(this));
      this.#manageCutButton = cut;
      cut.addEventListener("click", this.#cutPages.bind(this));
      this.#toggleMenuEntries(false);
      menuButton.disabled = true;
      eventBus.on("editingaction", ({
        name
      }) => {
        switch (name) {
          case "copyPage":
            this.#copyPages();
            break;
          case "cutPage":
            this.#cutPages();
            break;
          case "deletePage":
            this.#deletePages("delete");
            break;
          case "savePage":
            this.#saveExtractedPages();
            break;
        }
      }, internalOpt);
      this.container.addEventListener("contextmenu", e => {
        eventBus.dispatch("editingstateschanged", {
          source: this,
          details: {
            thumbnailId: parseInt(e.target.closest(".thumbnailImageContainer")?.parentElement.getAttribute("page-number"), 10) ?? -1,
            hasSelectedPages: !!this.#selectedPages?.size,
            canDeletePages: this.#canDelete()
          }
        });
      }, {
        signal: abortSignal,
        passive: true
      });
      this.#undoButton?.addEventListener("click", this.#undo.bind(this));
      this.#undoCloseButton?.addEventListener("click", this.#dismissUndo.bind(this, true));
      this.#deselectButton?.addEventListener("click", () => {
        this.#clearSelection();
        this.#toggleMenuEntries(false);
        this.#updateStatus("select");
      });
      this.#deselectButton.classList.toggle("hidden", true);
      if (this.#enableMerge && addFileComponent) {
        const {
          picker,
          button
        } = addFileComponent;
        picker.addEventListener("change", () => {
          const files = Array.from(picker.files ?? []);
          if (files.length) {
            this.#mergeFiles(files, this._currentPageNumber - 1);
          }
        });
        button.addEventListener("click", () => {
          picker.click();
        });
        this.#waitingBar.closeButton?.addEventListener("click", () => {
          this.#toggleBar("status");
          picker.value = "";
        });
      }
    } else {
      manageMenu.button.hidden = true;
    }
    this.scroll = watchScroll(this.scrollableContainer, this.#scrollUpdated.bind(this), abortSignal);
    this.#resetView();
    this.#addEventListeners();
  }
  #scrollUpdated() {
    this.renderingQueue.renderHighestPriority();
  }
  async #mergeFiles(files, insertAfter) {
    this.#toggleBar("waiting", "pdfjs-views-manager-waiting-for-file");
    const entries = [];
    for (const file of files) {
      const isImage = file.type?.startsWith("image/");
      if (!isImage && file.type !== "application/pdf") {
        const magic = await file.slice(0, 5).text();
        if (magic !== "%PDF-") {
          continue;
        }
      }
      if (isImage) {
        let bitmap;
        try {
          bitmap = await PDFThumbnailViewer.#fileToImageBitmap(file);
        } catch {
          continue;
        }
        entries.push({
          image: bitmap,
          insertAfter
        });
      } else {
        entries.push({
          document: await file.bytes(),
          insertAfter
        });
      }
    }
    if (entries.length === 0) {
      this.#toggleBar("status");
      return;
    }
    const pagesCount = this.#pagesMapper.pagesNumber;
    const data = this.hasStructuralChanges() ? this.getStructuralChanges() : {
      pageInfos: [{
        document: null
      }],
      copyLevels: null
    };
    data.pageInfos.push(...entries);
    this.eventBus.on("pagesloaded", () => {
      this.#selectedPages = null;
      this.#updateMenuEntries();
      this.#toggleBar("status");
      const newPagesCount = this.#pagesMapper.pagesNumber;
      const insertedPagesCount = newPagesCount - pagesCount;
      for (let i = insertAfter + 1, ii = insertAfter + 1 + insertedPagesCount; i < ii; i++) {
        this._thumbnails[i].checkbox.checked = true;
        this.#selectPage(i + 1, true);
      }
      if (insertedPagesCount) {
        this.#updateCurrentPage(insertAfter + 2, true);
      }
    }, {
      once: true,
      ...internalOpt
    });
    this.#reportTelemetry({
      action: "merge"
    });
    this.eventBus.dispatch("saveandload", {
      source: this,
      data
    });
  }
  getThumbnail(index) {
    return this._thumbnails[index];
  }
  #getVisibleThumbs() {
    return getVisibleElements({
      scrollEl: this.scrollableContainer,
      views: this._thumbnails
    });
  }
  #resetCurrentThumbnail(newPageNumber) {
    if (!this.pdfDocument) {
      return;
    }
    const thumbnailView = this._thumbnails[this._currentPageNumber - 1];
    thumbnailView?.toggleCurrent(false);
    this._currentPageNumber = newPageNumber;
  }
  scrollThumbnailIntoView(pageNumber) {
    if (!this.pdfDocument) {
      return;
    }
    const thumbnailView = this._thumbnails[pageNumber - 1];
    if (!thumbnailView) {
      console.error('scrollThumbnailIntoView: Invalid "pageNumber" parameter.');
      return;
    }
    if (pageNumber !== this._currentPageNumber) {
      this.#resetCurrentThumbnail(pageNumber);
      thumbnailView.toggleCurrent(true);
    }
    const {
      first,
      last,
      views
    } = this.#getVisibleThumbs();
    if (views.length > 0) {
      let shouldScroll = false;
      if (pageNumber <= first.id || pageNumber >= last.id) {
        shouldScroll = true;
      } else {
        for (const {
          id,
          percent
        } of views) {
          if (id !== pageNumber) {
            continue;
          }
          shouldScroll = percent < 100;
          break;
        }
      }
      if (shouldScroll) {
        thumbnailView.div.scrollIntoView(SCROLL_OPTIONS);
      }
    }
    this._currentPageNumber = pageNumber;
  }
  get pagesRotation() {
    return this._pagesRotation;
  }
  set pagesRotation(rotation) {
    if (!isValidRotation(rotation)) {
      throw new Error("Invalid thumbnails rotation angle.");
    }
    if (!this.pdfDocument) {
      return;
    }
    if (this._pagesRotation === rotation) {
      return;
    }
    this._pagesRotation = rotation;
    const updateArgs = {
      rotation
    };
    for (const thumbnail of this._thumbnails) {
      thumbnail.update(updateArgs);
    }
  }
  cleanup() {
    for (const thumbnail of this._thumbnails) {
      if (thumbnail.renderingState !== RenderingStates.FINISHED) {
        thumbnail.reset();
      }
    }
  }
  #resetView() {
    this._thumbnails = [];
    this._currentPageNumber = 1;
    this._pageLabels = null;
    this._pagesRotation = 0;
    this.container.textContent = "";
  }
  setDocument(pdfDocument) {
    if (this.pdfDocument) {
      this.#cancelRendering();
      this.#resetView();
    }
    this.pdfDocument = pdfDocument;
    if (!pdfDocument) {
      return;
    }
    this.#pagesMapper = pdfDocument.pagesMapper;
    const firstPagePromise = pdfDocument.getPage(1);
    const optionalContentConfigPromise = pdfDocument.getOptionalContentConfig({
      intent: "display"
    });
    firstPagePromise.then(firstPdfPage => {
      const pagesCount = pdfDocument.numPages;
      const viewport = firstPdfPage.getViewport({
        scale: 1
      });
      const fragment = document.createDocumentFragment();
      for (let pageNum = 1; pageNum <= pagesCount; ++pageNum) {
        const thumbnail = new PDFThumbnailView({
          container: fragment,
          eventBus: this.eventBus,
          id: pageNum,
          defaultViewport: viewport.clone(),
          optionalContentConfigPromise,
          linkService: this.linkService,
          renderingQueue: this.renderingQueue,
          maxCanvasPixels: this.maxCanvasPixels,
          maxCanvasDim: this.maxCanvasDim,
          pageColors: this.pageColors,
          enableSplitMerge: this.#enableSplitMerge
        });
        this._thumbnails.push(thumbnail);
      }
      this._thumbnails[0]?.setPdfPage(firstPdfPage);
      const thumbnailView = this._thumbnails[this._currentPageNumber - 1];
      thumbnailView.toggleCurrent(true);
      this.container.append(fragment);
      this.eventBus.dispatch("thumbnailsloaded", {
        source: this
      });
    }).catch(reason => {
      console.error("Unable to initialize thumbnail viewer", reason);
    });
  }
  #cancelRendering() {
    for (const thumbnail of this._thumbnails) {
      thumbnail.cancelRendering();
    }
  }
  setPageLabels(labels) {
    if (!this.pdfDocument) {
      return;
    }
    if (!labels) {
      this._pageLabels = null;
    } else if (!(Array.isArray(labels) && this.pdfDocument.numPages === labels.length)) {
      this._pageLabels = null;
      console.error("PDFThumbnailViewer_setPageLabels: Invalid page labels.");
    } else {
      this._pageLabels = labels;
    }
    for (let i = 0, ii = this._thumbnails.length; i < ii; i++) {
      this._thumbnails[i].setPageLabel(this._pageLabels?.[i] ?? null);
    }
  }
  async #ensurePdfPageLoaded(thumbView) {
    if (thumbView.pdfPage) {
      return thumbView.pdfPage;
    }
    try {
      const pdfPage = await this.pdfDocument.getPage(thumbView.id);
      if (!thumbView.pdfPage) {
        thumbView.setPdfPage(pdfPage);
      }
      return pdfPage;
    } catch (reason) {
      console.error("Unable to get page for thumb view", reason);
      return null;
    }
  }
  #getScrollAhead(visible) {
    if (visible.first?.id === 1) {
      return true;
    } else if (visible.last?.id === this._thumbnails.length) {
      return false;
    }
    return this.scroll.down;
  }
  forceRendering() {
    const visibleThumbs = this.#getVisibleThumbs();
    const scrollAhead = this.#getScrollAhead(visibleThumbs);
    const thumbView = this.renderingQueue.getHighestPriority(visibleThumbs, this._thumbnails, scrollAhead, false, true);
    if (thumbView) {
      this.#ensurePdfPageLoaded(thumbView).then(() => {
        this.renderingQueue.renderView(thumbView);
      });
      return true;
    }
    return false;
  }
  hasStructuralChanges() {
    return this.#pagesMapper?.hasBeenAltered() || false;
  }
  getStructuralChanges() {
    return this.#pagesMapper?.getPageMappingForSaving() || null;
  }
  static #getScaleFactor(image) {
    return PDFThumbnailViewer.#draggingScaleFactor ||= parseFloat(getComputedStyle(image).getPropertyValue("--thumbnail-dragging-scale"));
  }
  static #fitImageDimensions(width, height, {
    minSide = 0,
    maxSide
  }) {
    const longest = Math.max(width, height);
    let scale = 1;
    if (minSide > 0 && longest < minSide) {
      scale = minSide / longest;
    } else if (longest > maxSide) {
      scale = maxSide / longest;
    }
    return scale === 1 ? {
      width,
      height
    } : {
      width: Math.max(1, Math.round(width * scale)),
      height: Math.max(1, Math.round(height * scale))
    };
  }
  static async #fileToImageBitmap(file) {
    const MIN_RASTER_SIDE = 1024;
    const MAX_RASTER_SIDE = 4096;
    if (file.type !== "image/svg+xml") {
      const bitmap = await createImageBitmap(file);
      const {
        width,
        height
      } = PDFThumbnailViewer.#fitImageDimensions(bitmap.width, bitmap.height, {
        maxSide: MAX_RASTER_SIDE
      });
      if (width === bitmap.width && height === bitmap.height) {
        return bitmap;
      }
      const canvas = new OffscreenCanvas(width, height);
      const ctx = canvas.getContext("2d");
      ctx.drawImage(bitmap, 0, 0, width, height);
      bitmap.close();
      return canvas.transferToImageBitmap();
    }
    const url = URL.createObjectURL(file);
    try {
      const image = new Image();
      image.src = url;
      await image.decode();
      const {
        width,
        height
      } = PDFThumbnailViewer.#fitImageDimensions(image.naturalWidth || MIN_RASTER_SIDE, image.naturalHeight || MIN_RASTER_SIDE, {
        minSide: MIN_RASTER_SIDE,
        maxSide: MAX_RASTER_SIDE
      });
      const canvas = new OffscreenCanvas(width, height);
      const ctx = canvas.getContext("2d");
      ctx.drawImage(image, 0, 0, width, height);
      return canvas.transferToImageBitmap();
    } finally {
      URL.revokeObjectURL(url);
    }
  }
  #updateThumbnails(currentPageNumber) {
    this.#resetCurrentThumbnail(0);
    let newCurrentPageNumber = 0;
    const pagesMapper = this.#pagesMapper;
    const prevThumbnails = this.#savedThumbnails = this._thumbnails;
    const newThumbnails = this._thumbnails = [];
    const fragment = document.createDocumentFragment();
    const isCut = this.#isCut;
    for (let i = 1, ii = pagesMapper.pagesNumber; i <= ii; i++) {
      const prevPageNumber = pagesMapper.getPrevPageNumber(i);
      if (prevPageNumber < 0) {
        let thumbnail = this.#copiedThumbnails.get(-prevPageNumber);
        thumbnail.checkbox.checked = false;
        if (isCut) {
          thumbnail.updateId(i);
          fragment.append(thumbnail.div);
        } else {
          thumbnail = thumbnail.clone(fragment, i);
        }
        newThumbnails.push(thumbnail);
        continue;
      }
      if (prevPageNumber === currentPageNumber) {
        newCurrentPageNumber = i;
      }
      const newThumbnail = prevThumbnails[prevPageNumber - 1];
      newThumbnails.push(newThumbnail);
      newThumbnail.updateId(i);
      newThumbnail.checkbox.checked = false;
      fragment.append(newThumbnail.div);
    }
    this.container.replaceChildren(fragment);
    return newCurrentPageNumber;
  }
  #onStartDragging(draggedThumbnail) {
    this.#currentScrollTop = this.scrollableContainer.scrollTop;
    this.#currentScrollBottom = this.#currentScrollTop + this.scrollableContainer.clientHeight;
    this.#dragAC = new AbortController();
    this.container.classList.add("isDragging");
    this.#newBadge?.classList.add("hidden");
    const startPageNumber = parseInt(draggedThumbnail.getAttribute("page-number"), 10);
    this.#lastDraggedOverIndex = startPageNumber - 1;
    if (!this.#selectedPages?.has(startPageNumber)) {
      this.#pageNumberToRemove = startPageNumber;
      this.#selectPage(startPageNumber, true);
    }
    for (const selected of this.#selectedPages) {
      const thumbnail = this._thumbnails[selected - 1];
      const placeholder = thumbnail.placeholder = document.createElement("div");
      placeholder.classList.add("thumbnailImageContainer", "placeholder");
      const {
        div,
        imageContainer
      } = thumbnail;
      div.classList.add("isDragging");
      placeholder.style.height = getComputedStyle(imageContainer).height;
      imageContainer.after(placeholder);
      if (selected !== startPageNumber) {
        imageContainer.classList.add("hidden");
        continue;
      }
      if (this.#selectedPages.size === 1) {
        imageContainer.classList.add("draggingThumbnail");
        this.#draggedContainer = imageContainer;
        continue;
      }
      const draggedContainer = this.#draggedContainer = document.createElement("div");
      draggedContainer.classList.add("draggingThumbnail", "thumbnailImageContainer", "multiple");
      draggedContainer.style.height = getComputedStyle(imageContainer).height;
      imageContainer.replaceWith(draggedContainer);
      imageContainer.classList.remove("thumbnailImageContainer");
      draggedContainer.append(imageContainer);
      draggedContainer.setAttribute("data-multiple-count", this.#selectedPages.size);
    }
  }
  #onStopDragging(isDropping = false) {
    const draggedContainer = this.#draggedContainer;
    this.#draggedContainer = null;
    const lastDraggedOverIndex = this.#lastDraggedOverIndex;
    this.#lastDraggedOverIndex = NaN;
    this.#dragMarker?.remove();
    this.#dragMarker = null;
    this.#dragAC.abort();
    this.#dragAC = null;
    this.#newBadge?.classList.remove("hidden");
    this.container.classList.remove("isDragging");
    for (const selected of this.#selectedPages) {
      const thumbnail = this._thumbnails[selected - 1];
      const {
        div,
        placeholder,
        imageContainer
      } = thumbnail;
      placeholder.remove();
      imageContainer.classList.remove("draggingThumbnail", "hidden");
      div.classList.remove("isDragging");
    }
    if (draggedContainer.classList.contains("multiple")) {
      const originalImageContainer = draggedContainer.firstElementChild;
      draggedContainer.replaceWith(originalImageContainer);
      originalImageContainer.classList.add("thumbnailImageContainer");
    } else {
      draggedContainer.style.translate = "";
    }
    const selectedPages = this.#selectedPages;
    if (!isNaN(lastDraggedOverIndex) && isDropping && !(selectedPages.size === 1 && (selectedPages.has(lastDraggedOverIndex + 1) || selectedPages.has(lastDraggedOverIndex + 2)))) {
      this._thumbnails[this._currentPageNumber - 1]?.toggleCurrent(false);
      this._currentPageNumber = -1;
      const newIndex = lastDraggedOverIndex + 1;
      const pagesToMove = Array.from(selectedPages).sort((a, b) => a - b);
      const pagesMapper = this.#pagesMapper;
      const currentPageNumber = isNaN(this.#pageNumberToRemove) ? pagesToMove[0] : this.#pageNumberToRemove;
      pagesMapper.movePages(selectedPages, pagesToMove, newIndex);
      this.#updateCurrentPage(this.#updateThumbnails(currentPageNumber));
      this.#thumbnailsPositions = null;
      selectedPages.clear();
      this.#pageNumberToRemove = NaN;
      this.#toggleMenuEntries(false);
      this.#updateStatus("select");
      this.#reportTelemetry({
        action: "move"
      });
      this.eventBus.dispatch("pagesedited", {
        source: this,
        pagesMapper,
        type: "move"
      });
    }
    if (!isNaN(this.#pageNumberToRemove)) {
      this.#selectPage(this.#pageNumberToRemove, false);
      this.#pageNumberToRemove = NaN;
    }
  }
  #clearSelection() {
    for (const pageNumber of this.#selectedPages) {
      this._thumbnails[pageNumber - 1].toggleSelected(false);
    }
    this.#selectedPages.clear();
  }
  #updateCurrentPage(currentPageNumber, forceFocus = false) {
    setTimeout(() => {
      this.forceRendering();
      const newPageNumber = currentPageNumber || 1;
      this.linkService.goToPage(newPageNumber);
      const thumbnailView = this._thumbnails[newPageNumber - 1];
      if (forceFocus || !this.container.contains(document.activeElement)) {
        thumbnailView.imageContainer.focus();
      }
    }, 0);
  }
  #undo() {
    this.#clearSelection();
    this.#toggleMenuEntries(false);
    this.#updateStatus("select");
    if (this.#copiedThumbnails) {
      this.#copiedThumbnails = null;
      this.#pagesMapper.cancelCopy();
      this.#togglePasteMode(false);
      this.eventBus.dispatch("pagesedited", {
        source: this,
        pagesMapper: this.#pagesMapper,
        type: "cancelCopy"
      });
    }
    this.#isCut = false;
    if (this.#savedThumbnails) {
      const currentThumb = this._thumbnails[this._currentPageNumber - 1];
      currentThumb?.toggleCurrent(false);
      const fragment = document.createDocumentFragment();
      for (let i = 1, ii = this.#savedThumbnails.length; i <= ii; i++) {
        const thumbnail = this.#savedThumbnails[i - 1];
        thumbnail.updateId(i);
        thumbnail.checkbox.checked = false;
        fragment.append(thumbnail.div);
      }
      this.container.replaceChildren(fragment);
      this._thumbnails = this.#savedThumbnails;
      this.#savedThumbnails = null;
      const newIdx = currentThumb ? this._thumbnails.indexOf(currentThumb) : -1;
      this._currentPageNumber = newIdx + 1;
      currentThumb?.toggleCurrent(newIdx !== -1);
      this.#pagesMapper.cancelDelete();
      this.eventBus.dispatch("pagesedited", {
        source: this,
        pagesMapper: this.#pagesMapper,
        type: "cancelDelete"
      });
    }
  }
  #dismissUndo(mustUpdateStatus) {
    this.#copiedThumbnails = null;
    if (this.#deletedPageNumbers) {
      if (this.#savedThumbnails) {
        for (const pageNumber of this.#deletedPageNumbers) {
          this.#savedThumbnails[pageNumber - 1].destroy();
        }
        this.#savedThumbnails = null;
      }
      this.#deletedPageNumbers = null;
    }
    this.#isCut = false;
    if (mustUpdateStatus) {
      this.#updateStatus("select");
    }
    this.#togglePasteMode(false);
    this.#pagesMapper.cleanSavedData();
    this.eventBus.dispatch("pagesedited", {
      source: this,
      pagesMapper: this.#pagesMapper,
      type: "cleanSavedData"
    });
  }
  #canDelete() {
    const size = this.#selectedPages?.size || 0;
    return size > 0 && size < this._thumbnails.length;
  }
  #toggleBar(type, message, args) {
    const id = ++this.#toggleBarId;
    this.#hasUndoBarVisible = type === "undo";
    switch (type) {
      case "waiting":
        this.#waitingBar.label.setAttribute("data-l10n-id", message);
        break;
      case "undo":
        this.#undoLabel.setAttribute("data-l10n-id", message);
        if (args) {
          this.#undoLabel.setAttribute("data-l10n-args", JSON.stringify(args));
        }
        break;
      case "status":
        {
          const label = this.#statusLabel;
          message ||= label.getAttribute("data-l10n-id");
          this.#l10n.get(message, args).then(text => {
            if (id !== this.#toggleBarId) {
              return;
            }
            this.#l10n.pause();
            label.setAttribute("data-l10n-id", message);
            if (args) {
              label.setAttribute("data-l10n-args", JSON.stringify(args));
            } else {
              label.removeAttribute("data-l10n-args");
            }
            label.textContent = text;
            this.#l10n.resume();
            this.#showBar(type, !!args);
          });
          return;
        }
    }
    this.#showBar(type);
  }
  #showBar(type, hasSelection = false) {
    this.#statusBar.classList.toggle("hidden", type !== "status");
    this.#waitingBar.container.classList.toggle("hidden", type !== "waiting");
    this.#undoBar.classList.toggle("hidden", type !== "undo");
    if (type === "status") {
      this.#newBadge?.classList.toggle("hidden", hasSelection);
      this.#deselectButton.classList.toggle("hidden", !hasSelection);
    }
  }
  #togglePasteMode(enable) {
    this.#isInPasteMode = enable;
    if (enable) {
      this.container.classList.add("pasteMode");
      for (const thumbnail of this._thumbnails) {
        thumbnail.addPasteButton(this.#boundPastePages);
      }
    } else {
      this.container.classList.remove("pasteMode");
      for (const thumbnail of this._thumbnails) {
        thumbnail.removePasteButton();
      }
    }
  }
  #reportTelemetry(data) {
    this.eventBus.dispatch("reporttelemetry", {
      source: this,
      details: {
        type: "pageOrganization",
        data
      }
    });
  }
  #saveExtractedPages() {
    this.#reportTelemetry({
      action: "exportSelected"
    });
    this.eventBus.dispatch("saveextractedpages", {
      source: this,
      data: this.#pagesMapper.extractPages(this.#selectedPages)
    });
    this.#clearSelection();
    this.#toggleMenuEntries(false);
    this.#updateStatus("select");
  }
  #copyPages(clearSelection = true) {
    if (!this.#isCut) {
      this.#savedThumbnails = null;
      this.#reportTelemetry({
        action: "copy"
      });
    }
    this.#updateStatus(this.#isCut ? "cut" : "copy");
    const pageNumbersToCopy = this.#copiedPageNumbers = Uint32Array.from(this.#selectedPages).sort((a, b) => a - b);
    const pagesMapper = this.#pagesMapper;
    pagesMapper.copyPages(pageNumbersToCopy);
    this.#copiedThumbnails = new Map();
    for (const pageNumber of pageNumbersToCopy) {
      this.#copiedThumbnails.set(pageNumber, this._thumbnails[pageNumber - 1]);
    }
    this.eventBus.dispatch("pagesedited", {
      source: this,
      pagesMapper,
      pageNumbers: pageNumbersToCopy,
      type: "copy"
    });
    if (clearSelection) {
      this.#clearSelection();
    }
    this.#togglePasteMode(true);
    this.#toggleMenuEntries(false);
  }
  #cutPages() {
    if (!this.#canDelete()) {
      return;
    }
    this.#reportTelemetry({
      action: "cut"
    });
    this.#isCut = true;
    this.#copyPages(false);
    this.#deletePages("cut");
  }
  #pastePages(index) {
    this.#reportTelemetry({
      action: "paste"
    });
    const pagesMapper = this.#pagesMapper;
    const currentPageNumber = this.#copiedPageNumbers.includes(this._currentPageNumber) ? 0 : this._currentPageNumber;
    pagesMapper.pastePages(index);
    this.#updateThumbnails(currentPageNumber);
    this.#updateCurrentPage(index + 1, true);
    this.#thumbnailsPositions = null;
    this.eventBus.dispatch("pagesedited", {
      source: this,
      pagesMapper,
      hasBeenCut: this.#isCut,
      type: "paste"
    });
    this.#copiedThumbnails = null;
    this.#isCut = false;
    this.#togglePasteMode(false);
    this.#toggleMenuEntries(false);
    this.#updateStatus("select");
  }
  #deletePages(type = "delete") {
    if (!this.#canDelete()) {
      return;
    }
    const selectedPages = this.#selectedPages;
    if (type === "delete") {
      this.#reportTelemetry({
        action: "delete"
      });
      this.#updateStatus("delete");
    }
    const pagesMapper = this.#pagesMapper;
    const currentPageNumber = selectedPages.has(this._currentPageNumber) ? 0 : this._currentPageNumber;
    const pagesToDelete = this.#deletedPageNumbers = Uint32Array.from(selectedPages).sort((a, b) => a - b);
    pagesMapper.deletePages(pagesToDelete);
    this.#updateCurrentPage(this.#updateThumbnails(currentPageNumber));
    this.#thumbnailsPositions = null;
    selectedPages.clear();
    this.#updateMenuEntries();
    this.eventBus.dispatch("pagesedited", {
      source: this,
      pagesMapper,
      pageNumbers: pagesToDelete,
      type
    });
  }
  #updateMenuEntries() {
    const size = this.#selectedPages?.size || 0;
    this.#manageExportButton.disabled = this.#manageCopyButton.disabled = !size;
    this.#manageDeleteButton.disabled = this.#manageCutButton.disabled = !this.#canDelete();
  }
  #toggleMenuEntries(enable) {
    this.#manageExportButton.disabled = this.#manageDeleteButton.disabled = this.#manageCopyButton.disabled = this.#manageCutButton.disabled = !enable;
  }
  #updateStatus(type) {
    if (!this.#statusBar || !this.#undoBar) {
      return;
    }
    const count = this.#selectedPages?.size || 0;
    if (type === "select") {
      this.#toggleBar("status", count ? "pdfjs-views-manager-pages-status-action-label" : "pdfjs-views-manager-pages-status-none-action-label", count ? {
        count
      } : null);
      return;
    }
    let l10nId;
    switch (type) {
      case "copy":
        l10nId = "pdfjs-views-manager-pages-status-undo-copy-label";
        break;
      case "cut":
        l10nId = "pdfjs-views-manager-status-undo-cut-label";
        break;
      case "delete":
        l10nId = "pdfjs-views-manager-pages-status-undo-delete-label";
        break;
    }
    this.#toggleBar("undo", l10nId, {
      count
    });
    const isCopy = type === "copy";
    this.#undoButton.firstElementChild.setAttribute("data-l10n-id", isCopy ? "pdfjs-views-manager-status-done-button-label" : "pdfjs-views-manager-status-undo-button-label");
    this.#undoCloseButton.classList.toggle("hidden", isCopy);
  }
  #moveDraggedContainer(dx, dy) {
    if (this.#isOneColumnView) {
      dx = 0;
    }
    if (this.#draggedImageX + dx < 0 || this.#draggedImageX + this.#draggedImageWidth + dx > this.#scrollableContainerWidth) {
      dx = 0;
    }
    if (this.#draggedImageY + dy < 0 || this.#draggedImageY + this.#draggedImageHeight + dy > this.#scrollableContainerHeight) {
      dy = 0;
    }
    this.#draggedImageX += dx;
    this.#draggedImageY += dy;
    this.#draggedImageOffsetX += dx;
    this.#draggedImageOffsetY += dy;
    this.#draggedContainer.style.translate = `${this.#draggedImageOffsetX}px ${this.#draggedImageOffsetY}px`;
    if (this.#draggedImageY + this.#draggedImageHeight > this.#currentScrollBottom) {
      this.scrollableContainer.scrollTop = Math.min(this.scrollableContainer.scrollTop + PIXELS_TO_SCROLL_WHEN_DRAGGING, this.#scrollableContainerHeight);
    } else if (this.#draggedImageY < this.#currentScrollTop) {
      this.scrollableContainer.scrollTop = Math.max(this.scrollableContainer.scrollTop - PIXELS_TO_SCROLL_WHEN_DRAGGING, 0);
    }
    const positionData = this.#findClosestThumbnail(this.#draggedImageX + this.#draggedImageWidth / 2, this.#draggedImageY + this.#draggedImageHeight / 2);
    this.#positionDragMarker(positionData);
  }
  #positionDragMarker(positionData) {
    if (!positionData) {
      return;
    }
    let dragMarker = this.#dragMarker;
    if (!dragMarker) {
      dragMarker = this.#dragMarker = document.createElement("div");
      dragMarker.className = "dragMarker";
      this.container.firstChild.before(dragMarker);
    }
    const [index, space] = positionData;
    const dragMarkerStyle = dragMarker.style;
    const {
      bbox,
      x: xPos
    } = this.#thumbnailsPositions;
    let x, y, width, height;
    if (index < 0) {
      if (xPos.length === 1) {
        y = bbox[1] - SPACE_FOR_DRAG_MARKER_WHEN_NO_NEXT_ELEMENT;
        x = bbox[0];
        width = bbox[2];
      } else {
        y = bbox[1];
        x = bbox[0] - SPACE_FOR_DRAG_MARKER_WHEN_NO_NEXT_ELEMENT;
        height = bbox[3];
      }
    } else if (xPos.length === 1) {
      y = bbox[index * 4 + 1] + bbox[index * 4 + 3] + space;
      x = bbox[index * 4];
      width = bbox[index * 4 + 2];
    } else {
      y = bbox[index * 4 + 1];
      x = bbox[index * 4] + bbox[index * 4 + 2] + space;
      height = bbox[index * 4 + 3];
    }
    dragMarkerStyle.translate = `${x}px ${y}px`;
    dragMarkerStyle.width = width ? `${width}px` : "";
    dragMarkerStyle.height = height ? `${height}px` : "";
  }
  #computeThumbnailsPosition() {
    const positionsX = [];
    const positionsY = [];
    const positionsLastX = [];
    const bbox = new Float32Array(this._thumbnails.length * 4);
    let prevX = -Infinity;
    let prevY = -Infinity;
    let reminder = -1;
    let firstRightX;
    let lastRightX;
    let firstBottomY;
    for (let i = 0, ii = this._thumbnails.length; i < ii; i++) {
      const {
        div
      } = this._thumbnails[i];
      const {
        offsetTop: y,
        offsetLeft: x,
        offsetWidth: w,
        offsetHeight: h
      } = div;
      if (w === 0) {
        return;
      }
      bbox[i * 4] = x;
      bbox[i * 4 + 1] = y;
      bbox[i * 4 + 2] = w;
      bbox[i * 4 + 3] = h;
      if (x > prevX) {
        prevX = x + w / 2;
        firstRightX ??= prevX + w;
        positionsX.push(prevX);
      }
      if (y > prevY) {
        if (reminder === -1 && positionsX.length > 1) {
          reminder = ii % positionsX.length;
        }
        prevY = y + h / 2;
        firstBottomY ??= prevY + h;
        positionsY.push(prevY);
      }
      if (reminder > 0 && i >= ii - reminder) {
        const cx = x + w / 2;
        positionsLastX.push(cx);
        lastRightX ??= cx + w;
      }
    }
    let space;
    if (positionsX.length > 1) {
      space = (positionsX[1] - firstRightX) / 2;
    } else if (positionsY.length > 1) {
      space = (positionsY[1] - firstBottomY) / 2;
    } else {
      space = SPACE_FOR_DRAG_MARKER_WHEN_NO_NEXT_ELEMENT;
    }
    this.#thumbnailsPositions = {
      x: positionsX,
      y: positionsY,
      lastX: positionsLastX,
      space,
      lastSpace: positionsLastX.length ? (positionsLastX.at(-1) - lastRightX) / 2 : space,
      bbox
    };
    this.#isOneColumnView = positionsX.length === 1;
    ({
      clientWidth: this.#scrollableContainerWidth,
      scrollHeight: this.#scrollableContainerHeight
    } = this.scrollableContainer);
  }
  #addEventListeners() {
    this.eventBus.on("resize", ({
      source
    }) => {
      if (source.thumbnailsView === this.container) {
        this.#computeThumbnailsPosition();
      }
    }, internalOpt);
    this.container.addEventListener("keydown", e => {
      const {
        target
      } = e;
      const isCheckbox = target instanceof HTMLInputElement && target.type === "checkbox";
      switch (e.key) {
        case "ArrowLeft":
          this.#goToNextItem(target, false, true, isCheckbox);
          stopEvent(e);
          break;
        case "ArrowRight":
          this.#goToNextItem(target, true, true, isCheckbox);
          stopEvent(e);
          break;
        case "ArrowDown":
          this.#goToNextItem(target, true, false, isCheckbox);
          stopEvent(e);
          break;
        case "ArrowUp":
          this.#goToNextItem(target, false, false, isCheckbox);
          stopEvent(e);
          break;
        case "Home":
          this.#focusThumbnailElement(this._thumbnails[0], isCheckbox);
          stopEvent(e);
          break;
        case "End":
          this.#focusThumbnailElement(this._thumbnails.at(-1), isCheckbox);
          stopEvent(e);
          break;
        case "Enter":
        case " ":
          if (!isCheckbox) {
            this.#goToPage(e);
          }
          break;
        case "c":
          if (this.#enableSplitMerge && (e.ctrlKey || e.metaKey) && this.#selectedPages?.size) {
            this.#copyPages();
            stopEvent(e);
          }
          break;
        case "x":
          if (this.#enableSplitMerge && (e.ctrlKey || e.metaKey) && this.#selectedPages?.size) {
            this.#cutPages();
            stopEvent(e);
          }
          break;
        case "Delete":
        case "Backspace":
          if (this.#enableSplitMerge && !this.#isInPasteMode && this.#selectedPages?.size) {
            this.#deletePages();
            stopEvent(e);
          }
          break;
      }
    });
    this.container.addEventListener("click", e => {
      const {
        target
      } = e;
      if (target instanceof HTMLInputElement) {
        const pageNumber = parseInt(target.parentElement.getAttribute("page-number"), 10);
        this.#selectPage(pageNumber, target.checked);
        return;
      }
      this.#goToPage(e);
    });
    this.#addDragListeners();
    this.#addExternalFileDropListeners();
  }
  #selectPage(pageNumber, checked) {
    if (this.#hasUndoBarVisible) {
      this.#dismissUndo(false);
    }
    const set = this.#selectedPages ??= new Set();
    if (checked) {
      set.add(pageNumber);
    } else {
      set.delete(pageNumber);
    }
    this.#updateMenuEntries();
    this.#updateStatus("select");
  }
  #addDragListeners() {
    if (!this.#enableSplitMerge) {
      return;
    }
    this.container.addEventListener("pointerdown", e => {
      const {
        target: draggedImage,
        clientX: clickX,
        clientY: clickY,
        pointerId: dragPointerId
      } = e;
      if (e.button !== 0 || this.#isInPasteMode || this._thumbnails.length === 1 || !isNaN(this.#lastDraggedOverIndex) || !draggedImage.classList.contains("thumbnailImageContainer")) {
        return;
      }
      const thumbnail = draggedImage.parentElement;
      const pointerDownAC = new AbortController();
      const {
        signal: pointerDownSignal
      } = pointerDownAC;
      let prevDragX = clickX;
      let prevDragY = clickY;
      let prevScrollTop = this.scrollableContainer.scrollTop;
      const scaleFactor = PDFThumbnailViewer.#getScaleFactor(draggedImage);
      this.#draggedImageOffsetY = ((scaleFactor - 1) * e.layerY + draggedImage.offsetTop) / scaleFactor;
      if (this.#isOneColumnView) {
        this.#draggedImageOffsetX = draggedImage.offsetLeft + (scaleFactor - 1) * 0.5 * draggedImage.offsetWidth / scaleFactor;
      } else {
        this.#draggedImageOffsetX = ((scaleFactor - 1) * e.layerX + draggedImage.offsetLeft) / scaleFactor;
      }
      this.#draggedImageX = thumbnail.offsetLeft + this.#draggedImageOffsetX;
      this.#draggedImageY = thumbnail.offsetTop + this.#draggedImageOffsetY;
      this.#draggedImageWidth = draggedImage.offsetWidth / scaleFactor;
      this.#draggedImageHeight = draggedImage.offsetHeight / scaleFactor;
      this.container.addEventListener("pointermove", ev => {
        const {
          clientX: x,
          clientY: y,
          pointerId
        } = ev;
        if (isNaN(this.#lastDraggedOverIndex)) {
          if (pointerId !== dragPointerId || Math.abs(x - clickX) <= DRAG_THRESHOLD_IN_PIXELS && Math.abs(y - clickY) <= DRAG_THRESHOLD_IN_PIXELS) {
            return;
          }
          this.#onStartDragging(thumbnail);
          const stopDragging = (_e, isDropping = false) => {
            this.#onStopDragging(isDropping);
            pointerDownAC.abort();
          };
          const {
            signal
          } = this.#dragAC;
          window.addEventListener("touchmove", stopEvent, {
            passive: false,
            signal
          });
          window.addEventListener("contextmenu", noContextMenu, {
            signal
          });
          this.scrollableContainer.addEventListener("scrollend", () => {
            const {
              scrollableContainer: {
                clientHeight,
                scrollTop
              }
            } = this;
            this.#currentScrollTop = scrollTop;
            this.#currentScrollBottom = scrollTop + clientHeight;
            const dy = scrollTop - prevScrollTop;
            prevScrollTop = scrollTop;
            this.#moveDraggedContainer(0, dy);
          }, {
            passive: true,
            signal
          });
          window.addEventListener("pointerup", upEv => {
            if (upEv.pointerId !== dragPointerId) {
              return;
            }
            window.addEventListener("click", stopEvent, {
              capture: true,
              once: true,
              signal
            });
            stopEvent(upEv);
            stopDragging(upEv, true);
          }, {
            signal
          });
          window.addEventListener("blur", stopDragging, {
            signal
          });
          window.addEventListener("pointercancel", stopDragging, {
            signal
          });
          window.addEventListener("wheel", stopEvent, {
            passive: false,
            signal
          });
          window.addEventListener("keydown", kEv => {
            if (kEv.key === "Escape" && !isNaN(this.#lastDraggedOverIndex)) {
              stopDragging(kEv);
            }
          }, {
            signal
          });
        }
        const dx = x - prevDragX;
        const dy = y - prevDragY;
        prevDragX = x;
        prevDragY = y;
        this.#moveDraggedContainer(dx, dy);
      }, {
        passive: true,
        signal: pointerDownSignal
      });
      window.addEventListener("pointerup", ({
        pointerId
      }) => {
        if (pointerId !== dragPointerId) {
          return;
        }
        pointerDownAC.abort();
      }, {
        signal: pointerDownSignal
      });
      window.addEventListener("dragstart", stopEvent, {
        capture: true,
        signal: pointerDownSignal
      });
    });
  }
  #addExternalFileDropListeners() {
    if (!this.#enableMerge) {
      return;
    }
    const container = this.container;
    const signal = this.#abortSignal;
    const hasMergeableItem = dataTransfer => {
      if (!dataTransfer) {
        return false;
      }
      for (const item of dataTransfer.items) {
        if (item.kind === "file" && (item.type === "application/pdf" || item.type.startsWith("image/"))) {
          return true;
        }
      }
      return false;
    };
    const pointerInContainer = ({
      clientX,
      clientY
    }) => {
      const {
        left,
        right,
        top,
        bottom
      } = container.getBoundingClientRect();
      return clientX >= left && clientX < right && clientY >= top && clientY < bottom;
    };
    container.addEventListener("dragenter", e => {
      if (this.#externalDragActive || !isNaN(this.#lastDraggedOverIndex) || !this._thumbnails.length || !hasMergeableItem(e.dataTransfer)) {
        return;
      }
      e.preventDefault();
      e.stopPropagation();
      e.dataTransfer.dropEffect = "copy";
      this.#externalDragActive = true;
      this.container.classList.add("isDraggingFile");
      this.#thumbnailsPositions = null;
      this.#computeThumbnailsPosition();
      this.#lastDraggedOverIndex = NaN;
    }, {
      signal
    });
    container.addEventListener("dragover", e => {
      if (!this.#externalDragActive) {
        return;
      }
      e.preventDefault();
      e.stopPropagation();
      e.dataTransfer.dropEffect = "copy";
      if (!this.#thumbnailsPositions) {
        return;
      }
      const rect = container.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const positionData = this.#findClosestThumbnail(x, y);
      this.#positionDragMarker(positionData);
    }, {
      signal
    });
    container.addEventListener("dragleave", e => {
      if (!this.#externalDragActive) {
        return;
      }
      if (e.relatedTarget && container.contains(e.relatedTarget) || pointerInContainer(e)) {
        return;
      }
      this.#endExternalFileDrag();
    }, {
      signal
    });
    container.addEventListener("drop", e => {
      if (!this.#externalDragActive) {
        return;
      }
      e.preventDefault();
      e.stopPropagation();
      const files = Array.from(e.dataTransfer.files ?? []);
      if (isNaN(this.#lastDraggedOverIndex) && this.#thumbnailsPositions) {
        const rect = container.getBoundingClientRect();
        this.#findClosestThumbnail(e.clientX - rect.left, e.clientY - rect.top);
      }
      const insertAfter = isNaN(this.#lastDraggedOverIndex) ? -1 : this.#lastDraggedOverIndex;
      this.#endExternalFileDrag();
      if (files.length) {
        this.#mergeFiles(files, insertAfter);
      }
    }, {
      signal
    });
  }
  #endExternalFileDrag() {
    this.#externalDragActive = false;
    this.container.classList.remove("isDraggingFile");
    this.#dragMarker?.remove();
    this.#dragMarker = null;
    this.#lastDraggedOverIndex = NaN;
  }
  #goToPage(e) {
    const container = e.target.closest(".thumbnailImageContainer");
    if (container) {
      const pageNumber = parseInt(container.getAttribute("page-number"), 10);
      this.linkService.goToPage(pageNumber);
      stopEvent(e);
    }
  }
  #focusThumbnailElement(thumbnail, focusCheckbox) {
    if (focusCheckbox && thumbnail.checkbox) {
      thumbnail.checkbox.focus();
    } else {
      thumbnail.imageContainer.focus();
    }
  }
  #goToNextItem(element, forward, horizontal, navigateCheckboxes = false) {
    let currentPageNumber = parseInt(element.parentElement.getAttribute("page-number"), 10);
    if (isNaN(currentPageNumber)) {
      currentPageNumber = this._currentPageNumber;
    }
    const increment = forward ? 1 : -1;
    let nextThumbnail;
    if (horizontal) {
      const nextPageNumber = MathClamp(currentPageNumber + increment, 1, this._thumbnails.length + 1);
      nextThumbnail = this._thumbnails[nextPageNumber - 1];
    } else {
      const currentThumbnail = this._thumbnails[currentPageNumber - 1];
      const {
        x: currentX,
        y: currentY
      } = currentThumbnail.div.getBoundingClientRect();
      let firstWithDifferentY;
      for (let i = currentPageNumber - 1 + increment; i >= 0 && i < this._thumbnails.length; i += increment) {
        const thumbnail = this._thumbnails[i];
        const {
          x,
          y
        } = thumbnail.div.getBoundingClientRect();
        if (!firstWithDifferentY && y !== currentY) {
          firstWithDifferentY = thumbnail;
        }
        if (x === currentX) {
          nextThumbnail = thumbnail;
          break;
        }
      }
      nextThumbnail ??= firstWithDifferentY;
    }
    if (nextThumbnail) {
      this.#focusThumbnailElement(nextThumbnail, navigateCheckboxes);
    }
  }
  #findClosestThumbnail(x, y) {
    if (!this.#thumbnailsPositions) {
      this.#computeThumbnailsPosition();
    }
    const {
      x: positionsX,
      y: positionsY,
      lastX: positionsLastX,
      space: spaceBetweenThumbnails,
      lastSpace: lastSpaceBetweenThumbnails
    } = this.#thumbnailsPositions;
    const lastDraggedOverIndex = this.#lastDraggedOverIndex;
    let xPos = lastDraggedOverIndex % positionsX.length;
    let yPos = Math.floor(lastDraggedOverIndex / positionsX.length);
    let xArray = yPos === positionsY.length - 1 ? positionsLastX : positionsX;
    if (positionsY[yPos] <= y && y < (positionsY[yPos + 1] ?? Infinity) && xArray[xPos] <= x && x < (xArray[xPos + 1] ?? Infinity)) {
      return null;
    }
    let index;
    yPos = binarySearchFirstItem(positionsY, cy => y < cy);
    if (this.#isOneColumnView) {
      index = yPos - 1;
    } else {
      if (yPos === positionsY.length) {
        yPos = positionsY.length - 1;
      } else {
        const dist1 = Math.abs(positionsY[yPos - 1] - y);
        const dist2 = Math.abs(positionsY[yPos] - y);
        yPos = dist1 < dist2 ? yPos - 1 : yPos;
      }
      xArray = yPos === positionsY.length - 1 && positionsLastX.length > 0 ? positionsLastX : positionsX;
      xPos = binarySearchFirstItem(xArray, cx => x < cx) - 1;
      if (yPos < 0) {
        if (xPos <= 0) {
          xPos = -1;
        }
        yPos = 0;
      }
      index = MathClamp(yPos * positionsX.length + xPos, -1, this._thumbnails.length - 1);
    }
    if (index === lastDraggedOverIndex) {
      return null;
    }
    this.#lastDraggedOverIndex = index;
    const space = yPos === positionsY.length - 1 && positionsLastX.length > 0 && xPos >= 0 ? lastSpaceBetweenThumbnails : spaceBetweenThumbnails;
    return [index, space];
  }
}

;// ./web/annotation_editor_layer_builder.js


class AnnotationEditorLayerBuilder {
  #annotationLayer = null;
  #drawLayer = null;
  #onAppend = null;
  #structTreeLayer = null;
  #textLayer = null;
  #uiManager;
  constructor(options) {
    this.pageIndex = options.pageIndex;
    this.accessibilityManager = options.accessibilityManager;
    this.l10n = options.l10n;
    this.l10n ||= new genericl10n_GenericL10n();
    this.annotationEditorLayer = null;
    this.div = null;
    this._cancelled = false;
    this.#uiManager = options.uiManager;
    this.#annotationLayer = options.annotationLayer || null;
    this.#textLayer = options.textLayer || null;
    this.#drawLayer = options.drawLayer || null;
    this.#onAppend = options.onAppend || null;
    this.#structTreeLayer = options.structTreeLayer || null;
  }
  updatePageIndex(newPageIndex) {
    this.pageIndex = newPageIndex;
    this.annotationEditorLayer?.updatePageIndex(newPageIndex);
  }
  async render({
    viewport,
    intent = "display"
  }) {
    if (intent !== "display" || this._cancelled) {
      return;
    }
    const clonedViewport = viewport.clone({
      dontFlip: true
    });
    if (this.div) {
      this.annotationEditorLayer.update({
        viewport: clonedViewport
      });
      this.show();
      return;
    }
    const div = this.div = document.createElement("div");
    div.className = "annotationEditorLayer";
    div.hidden = true;
    div.dir = this.#uiManager.direction;
    this.#onAppend?.(div);
    this.annotationEditorLayer = new AnnotationEditorLayer({
      uiManager: this.#uiManager,
      div,
      structTreeLayer: this.#structTreeLayer,
      accessibilityManager: this.accessibilityManager,
      pageIndex: this.pageIndex,
      l10n: this.l10n,
      viewport: clonedViewport,
      annotationLayer: this.#annotationLayer,
      textLayer: this.#textLayer,
      drawLayer: this.#drawLayer
    });
    const parameters = {
      viewport: clonedViewport,
      div,
      annotations: null,
      intent
    };
    await this.annotationEditorLayer.render(parameters);
    this.show();
  }
  update(viewport) {
    if (this.div) {
      this.annotationEditorLayer.update({
        viewport: viewport.clone({
          dontFlip: true
        })
      });
    }
  }
  cancel() {
    this._cancelled = true;
    if (!this.div) {
      return;
    }
    this.annotationEditorLayer.destroy();
  }
  hide() {
    if (!this.div) {
      return;
    }
    this.annotationEditorLayer.pause(true);
    this.div.hidden = true;
  }
  show() {
    if (!this.div || this.annotationEditorLayer.isInvisible) {
      return;
    }
    this.div.hidden = false;
    this.annotationEditorLayer.pause(false);
  }
}

;// ./web/annotation_layer_builder.js



class AnnotationLayerBuilder {
  #annotations = null;
  #commentManager = null;
  #onAppend = null;
  #eventAC = null;
  #linksInjected = false;
  constructor({
    pdfPage,
    linkService,
    downloadManager,
    annotationStorage = null,
    imageResourcesPath = "",
    renderForms = true,
    enableComment = false,
    commentManager = null,
    enableScripting = false,
    hasJSActionsPromise = null,
    fieldObjectsPromise = null,
    annotationCanvasMap = null,
    accessibilityManager = null,
    annotationEditorUIManager = null,
    onAppend = null
  }) {
    this.pdfPage = pdfPage;
    this.linkService = linkService;
    this.downloadManager = downloadManager;
    this.imageResourcesPath = imageResourcesPath;
    this.renderForms = renderForms;
    this.annotationStorage = annotationStorage;
    this.enableComment = enableComment;
    this.#commentManager = commentManager;
    this.enableScripting = enableScripting;
    this._hasJSActionsPromise = hasJSActionsPromise || Promise.resolve(false);
    this._fieldObjectsPromise = fieldObjectsPromise || Promise.resolve(null);
    this._annotationCanvasMap = annotationCanvasMap;
    this._accessibilityManager = accessibilityManager;
    this._annotationEditorUIManager = annotationEditorUIManager;
    this.#onAppend = onAppend;
    this.annotationLayer = null;
    this.div = null;
    this._cancelled = false;
    this._eventBus = linkService.eventBus;
  }
  async render({
    viewport,
    intent = "display",
    structTreeLayer = null,
    optionalContentConfigPromise = null
  }) {
    if (this.div) {
      const optionalContentConfig = await optionalContentConfigPromise;
      if (this._cancelled || !this.annotationLayer) {
        return;
      }
      this.annotationLayer.update({
        viewport: viewport.clone({
          dontFlip: true
        }),
        optionalContentConfig
      });
      return;
    }
    const [annotations, hasJSActions, fieldObjects, optionalContentConfig] = await Promise.all([this.pdfPage.getAnnotations({
      intent
    }), this._hasJSActionsPromise, this._fieldObjectsPromise, optionalContentConfigPromise]);
    if (this._cancelled) {
      return;
    }
    const div = this.div = document.createElement("div");
    div.className = "annotationLayer";
    this.#onAppend?.(div);
    this.annotationLayer = new AnnotationLayer({
      div,
      accessibilityManager: this._accessibilityManager,
      annotationCanvasMap: this._annotationCanvasMap,
      annotationEditorUIManager: this._annotationEditorUIManager,
      annotationStorage: this.annotationStorage,
      page: this.pdfPage,
      viewport: viewport.clone({
        dontFlip: true
      }),
      structTreeLayer,
      commentManager: this.#commentManager,
      linkService: this.linkService
    });
    if (annotations.length === 0) {
      this.#annotations = annotations;
      setLayerDimensions(this.div, viewport);
      return;
    }
    await this.annotationLayer.render({
      annotations,
      imageResourcesPath: this.imageResourcesPath,
      renderForms: this.renderForms,
      downloadManager: this.downloadManager,
      enableComment: this.enableComment,
      enableAnnotationEditing: true,
      enableScripting: this.enableScripting,
      hasJSActions,
      fieldObjects,
      optionalContentConfig
    });
    this.#annotations = annotations;
    if (this.linkService.isInPresentationMode) {
      this.#updatePresentationModeState(PresentationModeState.FULLSCREEN);
    }
    if (!this.#eventAC) {
      this.#eventAC = new AbortController();
      this._eventBus?.on("presentationmodechanged", evt => {
        this.#updatePresentationModeState(evt.state);
      }, {
        signal: this.#eventAC.signal,
        ...internalOpt
      });
    }
  }
  cancel() {
    this._cancelled = true;
    this.#eventAC?.abort();
    this.#eventAC = null;
    this.annotationLayer?.destroy();
  }
  refreshCanvases() {
    this.annotationLayer?.refreshCanvases();
  }
  hide() {
    if (!this.div) {
      return;
    }
    this.div.hidden = true;
  }
  hasEditableAnnotations() {
    return !!this.annotationLayer?.hasEditableAnnotations();
  }
  async injectLinkAnnotations(inferredLinks) {
    if (this.#annotations === null) {
      throw new Error("`render` method must be called before `injectLinkAnnotations`.");
    }
    if (this._cancelled || this.#linksInjected) {
      return;
    }
    this.#linksInjected = true;
    if (!inferredLinks.length) {
      return;
    }
    let newLinks;
    if (this.#annotations.length) {
      newLinks = this.#checkInferredLinks(inferredLinks);
      if (!newLinks.length) {
        return;
      }
    } else {
      newLinks = inferredLinks;
    }
    await this.annotationLayer.addLinkAnnotations(newLinks);
  }
  get linksInjected() {
    return this.#linksInjected;
  }
  #updatePresentationModeState(state) {
    if (!this.div) {
      return;
    }
    let disableFormElements = false;
    switch (state) {
      case PresentationModeState.FULLSCREEN:
        disableFormElements = true;
        break;
      case PresentationModeState.NORMAL:
        break;
      default:
        return;
    }
    for (const section of this.div.childNodes) {
      if (section.hasAttribute("data-internal-link") || section.classList.contains("mediaAnnotation")) {
        continue;
      }
      section.inert = disableFormElements;
    }
  }
  #checkInferredLinks(inferredLinks) {
    function annotationRects(annot) {
      if (!annot.quadPoints) {
        return [annot.rect];
      }
      const rects = [];
      for (let i = 2, ii = annot.quadPoints.length; i < ii; i += 8) {
        const trX = annot.quadPoints[i];
        const trY = annot.quadPoints[i + 1];
        const blX = annot.quadPoints[i + 2];
        const blY = annot.quadPoints[i + 3];
        rects.push([blX, blY, trX, trY]);
      }
      return rects;
    }
    function intersectAnnotations(annot1, annot2) {
      const intersections = [];
      const annot1Rects = annotationRects(annot1);
      const annot2Rects = annotationRects(annot2);
      for (const rect1 of annot1Rects) {
        for (const rect2 of annot2Rects) {
          const intersection = Util.intersect(rect1, rect2);
          if (intersection) {
            intersections.push(intersection);
          }
        }
      }
      return intersections;
    }
    function areaRects(rects) {
      let totalArea = 0;
      for (const rect of rects) {
        totalArea += Math.abs((rect[2] - rect[0]) * (rect[3] - rect[1]));
      }
      return totalArea;
    }
    return inferredLinks.filter(link => {
      let linkAreaRects;
      for (const annotation of this.#annotations) {
        if (annotation.annotationType !== AnnotationType.LINK) {
          continue;
        }
        const intersections = intersectAnnotations(annotation, link);
        if (intersections.length === 0) {
          continue;
        }
        linkAreaRects ??= areaRects(annotationRects(link));
        if (areaRects(intersections) / linkAreaRects > 0.5) {
          return false;
        }
      }
      return true;
    });
  }
}

;// ./web/autolinker.js


function DOMRectToPDF({
  width,
  height,
  left,
  top
}, pdfPageView) {
  if (width === 0 || height === 0) {
    return null;
  }
  const pageBox = pdfPageView.textLayer.div.getBoundingClientRect();
  const bottomLeft = pdfPageView.getPagePoint(left - pageBox.left, top - pageBox.top);
  const topRight = pdfPageView.getPagePoint(left - pageBox.left + width, top - pageBox.top + height);
  return Util.normalizeRect([bottomLeft[0], bottomLeft[1], topRight[0], topRight[1]]);
}
function calculateLinkPosition(range, pdfPageView) {
  const rangeRects = range.getClientRects();
  if (rangeRects.length === 1) {
    return {
      rect: DOMRectToPDF(rangeRects[0], pdfPageView)
    };
  }
  const rect = [Infinity, Infinity, -Infinity, -Infinity];
  const quadPoints = [];
  let i = 0;
  for (const domRect of rangeRects) {
    const normalized = DOMRectToPDF(domRect, pdfPageView);
    if (normalized === null) {
      continue;
    }
    quadPoints[i] = quadPoints[i + 4] = normalized[0];
    quadPoints[i + 1] = quadPoints[i + 3] = normalized[3];
    quadPoints[i + 2] = quadPoints[i + 6] = normalized[2];
    quadPoints[i + 5] = quadPoints[i + 7] = normalized[1];
    Util.rectBoundingBox(...normalized, rect);
    i += 8;
  }
  return {
    quadPoints,
    rect
  };
}
function textPosition(container, offset) {
  let currentContainer = container;
  do {
    if (currentContainer.nodeType === Node.TEXT_NODE) {
      const currentLength = currentContainer.textContent.length;
      if (offset <= currentLength) {
        return [currentContainer, offset];
      }
      offset -= currentLength;
    } else if (currentContainer.firstChild) {
      currentContainer = currentContainer.firstChild;
      continue;
    }
    while (!currentContainer.nextSibling && currentContainer !== container) {
      currentContainer = currentContainer.parentNode;
    }
    if (currentContainer !== container) {
      currentContainer = currentContainer.nextSibling;
    }
  } while (currentContainer !== container);
  throw new Error("Offset is bigger than container's contents length.");
}
class Autolinker {
  static #index = 0;
  static #regex;
  static #numericTLDRegex;
  static findLinks(text) {
    this.#regex ??= /\b(?:https?:\/\/|mailto:|www\.)(?:[\S--[\p{P}<>]]|\/|[\S--[\[\]]]+[\S--[\p{P}<>]])+|(?=\p{L})[\S--[@\p{Ps}\p{Pe}<>]]{1,64}@([\S--[[\p{P}--\-]<>]]{1,63}(?:\.[\S--[[\p{P}--\-]<>]]{1,63})+)/gv;
    const [normalizedText, diffs] = normalize(text, {
      ignoreDashEOL: true
    });
    const matches = normalizedText.matchAll(this.#regex);
    const links = [];
    for (const match of matches) {
      const [url, emailDomain] = match;
      let raw;
      if (url.startsWith("www.") || url.startsWith("http://") || url.startsWith("https://")) {
        raw = url;
      } else if (emailDomain) {
        const hostname = URL.parse(`http://${emailDomain}`)?.hostname;
        if (!hostname) {
          continue;
        }
        this.#numericTLDRegex ??= /\.\d+$/;
        if (this.#numericTLDRegex.test(hostname)) {
          continue;
        }
      }
      raw ??= url.startsWith("mailto:") ? url : `mailto:${url}`;
      const absoluteURL = createValidAbsoluteUrl(raw, null, {
        addDefaultProtocol: true
      });
      if (absoluteURL) {
        const [index, length] = getOriginalIndex(diffs, match.index, url.length);
        links.push({
          url: absoluteURL.href,
          index,
          length
        });
      }
    }
    return links;
  }
  static processLinks(pdfPageView) {
    const highlighter = pdfPageView._textHighlighter;
    const textContent = highlighter.textContentItemsStr.join("\n");
    if (!textContent) {
      return [];
    }
    const links = this.findLinks(textContent);
    if (!links.length) {
      return [];
    }
    const matches = highlighter._convertMatches(links.map(({
      index
    }) => index), links.map(({
      length
    }) => length));
    const {
      textDivs
    } = highlighter;
    const range = new Range();
    return links.map(({
      url
    }, i) => {
      const {
        begin,
        end
      } = matches[i];
      range.setStart(...textPosition(textDivs[begin.divIdx], begin.offset));
      range.setEnd(...textPosition(textDivs[end.divIdx], end.offset));
      return {
        id: `inferred_link_${this.#index++}`,
        unsafeUrl: url,
        url,
        annotationType: AnnotationType.LINK,
        rotation: 0,
        ...calculateLinkPosition(range, pdfPageView),
        borderStyle: null
      };
    });
  }
}

;// ./web/base_pdf_page_view.js


class BasePDFPageView extends RenderableView {
  #loadingId = null;
  #renderError = null;
  #renderingState = RenderingStates.INITIAL;
  #showCanvas = null;
  #startTime = 0;
  #tempCanvas = null;
  canvas = null;
  div = null;
  enableOptimizedPartialRendering = false;
  enableSelectionRendering = true;
  imagesRightClickMinSize = -1;
  eventBus = null;
  id = null;
  imageCoordinates = null;
  pageColors = null;
  recordedBBoxes = null;
  renderingQueue = null;
  constructor(options) {
    super();
    this.eventBus = options.eventBus;
    this.id = options.id;
    this.pageColors = options.pageColors || null;
    this.renderingQueue = options.renderingQueue;
    this.enableOptimizedPartialRendering = options.enableOptimizedPartialRendering ?? false;
    this.enableSelectionRendering = options.enableSelectionRendering !== false && FeatureTest.isBackdropFilterSupported;
    this.imagesRightClickMinSize = options.imagesRightClickMinSize ?? -1;
    this.minDurationToUpdateCanvas = options.minDurationToUpdateCanvas ?? 500;
  }
  get renderingState() {
    return this.#renderingState;
  }
  set renderingState(state) {
    if (state === this.#renderingState) {
      return;
    }
    this.#renderingState = state;
    if (this.#loadingId) {
      clearTimeout(this.#loadingId);
      this.#loadingId = null;
    }
    switch (state) {
      case RenderingStates.PAUSED:
        this.div.classList.remove("loading");
        this.#startTime = 0;
        if (!this.renderTask?.isWorkerRendering) {
          this.#showCanvas?.(false);
        }
        break;
      case RenderingStates.RUNNING:
        this.div.classList.add("loadingIcon");
        this.#loadingId = setTimeout(() => {
          this.div.classList.add("loading");
          this.#loadingId = null;
        }, 0);
        this.#startTime = Date.now();
        break;
      case RenderingStates.INITIAL:
      case RenderingStates.FINISHED:
        this.div.classList.remove("loadingIcon", "loading");
        this.#startTime = 0;
        break;
    }
  }
  _createCanvas(onShow, hideUntilComplete = false) {
    const {
      pageColors
    } = this;
    const hasHCM = !!(pageColors?.background && pageColors?.foreground);
    const prevCanvas = this.canvas;
    const updateOnFirstShow = !prevCanvas && !hasHCM && !hideUntilComplete;
    let canvas = this.canvas = document.createElement("canvas");
    this.#showCanvas = isLastShow => {
      if (updateOnFirstShow) {
        let tempCanvas = this.#tempCanvas;
        if (!isLastShow && this.minDurationToUpdateCanvas > 0 && !this.renderTask?.isWorkerRendering) {
          if (Date.now() - this.#startTime < this.minDurationToUpdateCanvas) {
            return;
          }
          if (!tempCanvas) {
            tempCanvas = this.#tempCanvas = canvas;
            canvas = this.canvas = canvas.cloneNode(false);
            onShow(canvas);
          }
        }
        if (tempCanvas) {
          const ctx = canvas.getContext("2d", {
            alpha: false
          });
          ctx.drawImage(tempCanvas, 0, 0);
          if (isLastShow) {
            this.#resetTempCanvas();
          } else {
            this.#startTime = Date.now();
          }
          return;
        }
        onShow(canvas);
        this.#showCanvas = null;
        return;
      }
      if (!isLastShow) {
        return;
      }
      if (prevCanvas) {
        prevCanvas.replaceWith(canvas);
        prevCanvas.width = prevCanvas.height = 0;
      } else {
        onShow(canvas);
      }
    };
    return {
      canvas,
      prevCanvas
    };
  }
  #renderContinueCallback = cont => {
    if (!this.renderTask?.isWorkerRendering) {
      this.#showCanvas?.(false);
    }
    if (this.renderingQueue && !this.renderingQueue.isHighestPriority(this)) {
      this.renderingState = RenderingStates.PAUSED;
      this.resume = () => {
        this.renderingState = RenderingStates.RUNNING;
        cont();
      };
      return;
    }
    cont();
  };
  _resetCanvas() {
    const {
      canvas
    } = this;
    if (!canvas) {
      return;
    }
    canvas.remove();
    canvas.width = canvas.height = 0;
    this.canvas = null;
    this.#resetTempCanvas();
  }
  #resetTempCanvas() {
    if (this.#tempCanvas) {
      this.#tempCanvas.width = this.#tempCanvas.height = 0;
      this.#tempCanvas = null;
    }
  }
  async _drawCanvas(options, onCancel, onFinish) {
    const renderTask = this.renderTask = this.pdfPage.render(options);
    renderTask.onContinue = this.#renderContinueCallback;
    renderTask.onFrame = () => this.#showCanvas?.(false);
    renderTask.onError = error => {
      if (error instanceof RenderingCancelledException) {
        onCancel();
        this.#renderError = null;
      }
    };
    let error = null;
    try {
      await renderTask.promise;
      this.#showCanvas?.(true);
    } catch (e) {
      if (e instanceof RenderingCancelledException) {
        return;
      }
      error = e;
      this.#showCanvas?.(true);
    } finally {
      this.#renderError = error;
      if (renderTask === this.renderTask) {
        this.renderTask = null;
        if (this.enableOptimizedPartialRendering) {
          this.recordedBBoxes ??= renderTask.recordedBBoxes;
        }
        if (this.imagesRightClickMinSize !== -1) {
          this.imageCoordinates ??= this.pdfPage.imageCoordinates;
        }
      }
    }
    this.renderingState = RenderingStates.FINISHED;
    onFinish(renderTask);
    if (error) {
      throw error;
    }
  }
  cancelRendering({
    cancelExtraDelay = 0
  } = {}) {
    if (this.renderTask) {
      this.renderTask.cancel(cancelExtraDelay);
      this.renderTask = null;
    }
    this.resume = null;
  }
  dispatchPageRender() {
    this.eventBus.dispatch("pagerender", {
      source: this,
      pageNumber: this.id
    });
  }
  dispatchPageRendered(cssTransform, isDetailView) {
    this.eventBus.dispatch("pagerendered", {
      source: this,
      pageNumber: this.id,
      cssTransform,
      isDetailView,
      timestamp: performance.now(),
      error: this.#renderError
    });
  }
}

;// ./web/draw_layer_builder.js

class DrawLayerBuilder {
  #drawLayer = null;
  constructor(options) {
    this.pageIndex = options.pageIndex;
    this.textLayer = options.textLayer || null;
    this.filterFactory = options.filterFactory || null;
    this.pageColors = options.pageColors || null;
  }
  async render({
    intent = "display"
  }) {
    if (intent !== "display" || this.#drawLayer || this._cancelled) {
      return;
    }
    this.#drawLayer = new DrawLayer({
      pageIndex: this.pageIndex,
      textLayer: this.textLayer,
      filterFactory: this.filterFactory,
      pageColors: this.pageColors
    });
  }
  cancel() {
    this._cancelled = true;
    this.#drawLayer?.destroy();
    this.#drawLayer = null;
  }
  setParent(parent) {
    this.#drawLayer?.setParent(parent);
  }
  getDrawLayer() {
    return this.#drawLayer;
  }
}

;// ./web/pdf_page_detail_view.js



class PDFPageDetailView extends BasePDFPageView {
  #detailArea = null;
  renderingCancelled = false;
  constructor({
    pageView
  }) {
    super(pageView);
    this.pageView = pageView;
    this.renderingId = "detail" + this.id;
    this.div = pageView.div;
  }
  setPdfPage(pdfPage) {
    this.pageView.setPdfPage(pdfPage);
  }
  get pdfPage() {
    return this.pageView.pdfPage;
  }
  get renderingState() {
    return super.renderingState;
  }
  set renderingState(state) {
    this.renderingCancelled = false;
    super.renderingState = state;
  }
  reset({
    keepCanvas = false
  } = {}) {
    const renderingCancelled = this.renderingCancelled || this.renderingState === RenderingStates.RUNNING || this.renderingState === RenderingStates.PAUSED;
    this.cancelRendering();
    this.renderingState = RenderingStates.INITIAL;
    this.renderingCancelled = renderingCancelled;
    if (!keepCanvas) {
      this._resetCanvas();
    }
  }
  #shouldRenderDifferentArea(visibleArea) {
    if (!this.#detailArea) {
      return true;
    }
    const minDetailX = this.#detailArea.minX;
    const minDetailY = this.#detailArea.minY;
    const maxDetailX = this.#detailArea.width + minDetailX;
    const maxDetailY = this.#detailArea.height + minDetailY;
    if (visibleArea.minX < minDetailX || visibleArea.minY < minDetailY || visibleArea.maxX > maxDetailX || visibleArea.maxY > maxDetailY) {
      return true;
    }
    const {
      width: maxWidth,
      height: maxHeight,
      scale
    } = this.pageView.viewport;
    if (this.#detailArea.scale !== scale) {
      return true;
    }
    const paddingLeftSize = visibleArea.minX - minDetailX;
    const paddingRightSize = maxDetailX - visibleArea.maxX;
    const paddingTopSize = visibleArea.minY - minDetailY;
    const paddingBottomSize = maxDetailY - visibleArea.maxY;
    const MOVEMENT_THRESHOLD = 0.5;
    const ratio = (1 + MOVEMENT_THRESHOLD) / MOVEMENT_THRESHOLD;
    if (minDetailX > 0 && paddingRightSize / paddingLeftSize > ratio || maxDetailX < maxWidth && paddingLeftSize / paddingRightSize > ratio || minDetailY > 0 && paddingBottomSize / paddingTopSize > ratio || maxDetailY < maxHeight && paddingTopSize / paddingBottomSize > ratio) {
      return true;
    }
    return false;
  }
  update({
    visibleArea = null,
    underlyingViewUpdated = false
  } = {}) {
    if (underlyingViewUpdated) {
      this.cancelRendering();
      this.renderingState = RenderingStates.INITIAL;
      return;
    }
    if (!this.#shouldRenderDifferentArea(visibleArea)) {
      return;
    }
    const {
      viewport,
      maxCanvasPixels,
      capCanvasAreaFactor
    } = this.pageView;
    const visibleWidth = visibleArea.maxX - visibleArea.minX;
    const visibleHeight = visibleArea.maxY - visibleArea.minY;
    const visiblePixels = visibleWidth * visibleHeight * OutputScale.pixelRatio ** 2;
    const maxDetailToVisibleLinearRatio = Math.sqrt(OutputScale.capPixels(maxCanvasPixels, capCanvasAreaFactor) / visiblePixels);
    const maxOverflowScale = (maxDetailToVisibleLinearRatio - 1) / 2;
    let overflowScale = Math.min(1, maxOverflowScale);
    if (overflowScale < 0) {
      overflowScale = 0;
    }
    const overflowWidth = visibleWidth * overflowScale;
    const overflowHeight = visibleHeight * overflowScale;
    const minX = Math.max(0, visibleArea.minX - overflowWidth);
    const maxX = Math.min(viewport.width, visibleArea.maxX + overflowWidth);
    const minY = Math.max(0, visibleArea.minY - overflowHeight);
    const maxY = Math.min(viewport.height, visibleArea.maxY + overflowHeight);
    const width = maxX - minX;
    const height = maxY - minY;
    this.#detailArea = {
      minX,
      minY,
      width,
      height,
      scale: viewport.scale
    };
    this.reset({
      keepCanvas: true
    });
  }
  _getRenderingContext(canvas, transform) {
    const baseContext = this.pageView._getRenderingContext(canvas, transform, false);
    const recordedBBoxes = this.pdfPage.recordedBBoxes;
    if (!recordedBBoxes || !this.enableOptimizedPartialRendering) {
      return baseContext;
    }
    const {
      viewport: {
        width: vWidth,
        height: vHeight
      }
    } = this.pageView;
    const {
      width: aWidth,
      height: aHeight,
      minX: aMinX,
      minY: aMinY
    } = this.#detailArea;
    const detailMinX = aMinX / vWidth;
    const detailMinY = aMinY / vHeight;
    const detailMaxX = (aMinX + aWidth) / vWidth;
    const detailMaxY = (aMinY + aHeight) / vHeight;
    return {
      ...baseContext,
      operationsFilter(index) {
        if (recordedBBoxes.isEmpty(index)) {
          return false;
        }
        return recordedBBoxes.minX(index) <= detailMaxX && recordedBBoxes.maxX(index) >= detailMinX && recordedBBoxes.minY(index) <= detailMaxY && recordedBBoxes.maxY(index) >= detailMinY;
      }
    };
  }
  async draw() {
    if (this.pageView.detailView !== this) {
      return undefined;
    }
    const hideUntilComplete = this.pageView.renderingState === RenderingStates.FINISHED || this.renderingState === RenderingStates.FINISHED;
    if (this.renderingState !== RenderingStates.INITIAL) {
      console.error("Must be in new state before drawing");
      this.reset();
    }
    const {
      div,
      pdfPage,
      viewport
    } = this.pageView;
    if (!pdfPage) {
      this.renderingState = RenderingStates.FINISHED;
      throw new Error("pdfPage is not loaded");
    }
    this.renderingState = RenderingStates.RUNNING;
    const canvasWrapper = this.pageView._ensureCanvasWrapper();
    const {
      canvas,
      prevCanvas
    } = this._createCanvas(newCanvas => {
      if (canvasWrapper.firstElementChild?.tagName === "CANVAS") {
        canvasWrapper.firstElementChild.after(newCanvas);
      } else {
        canvasWrapper.prepend(newCanvas);
      }
    }, hideUntilComplete);
    canvas.ariaHidden = true;
    if (this.enableOptimizedPartialRendering) {
      canvas.className = "detailView";
    }
    const {
      width,
      height
    } = viewport;
    const area = this.#detailArea;
    const {
      pixelRatio
    } = OutputScale;
    const transform = [pixelRatio, 0, 0, pixelRatio, -area.minX * pixelRatio, -area.minY * pixelRatio];
    canvas.width = area.width * pixelRatio;
    canvas.height = area.height * pixelRatio;
    const {
      style
    } = canvas;
    style.width = `${area.width * 100 / width}%`;
    style.height = `${area.height * 100 / height}%`;
    style.top = `${area.minY * 100 / height}%`;
    style.left = `${area.minX * 100 / width}%`;
    const renderingPromise = this._drawCanvas(this._getRenderingContext(canvas, transform), () => {
      this._resetCanvas();
      this.canvas = prevCanvas;
    }, () => {
      this.pageView._refreshAnnotationLayer();
      this.dispatchPageRendered(false, true);
    });
    div.setAttribute("data-loaded", true);
    this.dispatchPageRender();
    return renderingPromise;
  }
}

;// ./web/struct_tree_layer_builder.js


const PDF_ROLE_TO_HTML_ROLE = {
  Document: null,
  DocumentFragment: null,
  Part: "group",
  Art: "article",
  Sect: "group",
  Div: "group",
  BlockQuote: "blockquote",
  Aside: "note",
  NonStruct: "none",
  P: "paragraph",
  H: "heading",
  Title: null,
  FENote: "note",
  Sub: "group",
  Lbl: null,
  Span: null,
  Em: "emphasis",
  Strong: "strong",
  Note: "note",
  Code: "code",
  Link: "link",
  Annot: "note",
  Form: "form",
  Ruby: null,
  RB: null,
  RT: null,
  RP: null,
  Warichu: null,
  WT: null,
  WP: null,
  L: "list",
  LI: "listitem",
  LBody: null,
  Table: "table",
  TR: "row",
  TH: "columnheader",
  TD: "cell",
  THead: "rowgroup",
  TBody: "rowgroup",
  TFoot: "rowgroup",
  Caption: "caption",
  Figure: "figure",
  Formula: null,
  Artifact: null
};
const ARIA_ROLES_WITH_PROHIBITED_NAMES = new Set(["caption", "code", "emphasis", "generic", "none", "paragraph", "strong"]);
const MathMLElements = new Set(["math", "merror", "mfrac", "mi", "mmultiscripts", "mn", "mo", "mover", "mpadded", "mprescripts", "mroot", "mrow", "ms", "mspace", "msqrt", "mstyle", "msub", "msubsup", "msup", "mtable", "mtd", "mtext", "mtr", "munder", "munderover", "semantics"]);
const MathMLNamespace = "http://www.w3.org/1998/Math/MathML";
class MathMLSanitizer {
  static get sanitizer() {
    return shadow(this, "sanitizer", FeatureTest.isSanitizerSupported ? new Sanitizer({
      elements: Array.from(MathMLElements.keys(), name => ({
        name,
        namespace: MathMLNamespace
      })),
      replaceWithChildrenElements: [{
        name: "maction",
        namespace: MathMLNamespace
      }],
      attributes: ["dir", "displaystyle", "mathbackground", "mathcolor", "mathsize", "scriptlevel", "encoding", "display", "linethickness", "intent", "arg", "form", "fence", "separator", "lspace", "rspace", "stretchy", "symmetric", "maxsize", "minsize", "largeop", "movablelimits", "width", "height", "depth", "voffset", "accent", "accentunder", "columnspan", "rowspan"],
      comments: false
    }) : null);
  }
}
const HEADING_PATTERN = /^H(\d+)$/;
class StructTreeLayerBuilder {
  #promise;
  #treeDom = null;
  #treePromise;
  #annotationIds = new Set();
  #elementAttributes = new Map();
  #pendingLinkOwnership = new Map();
  #linkTextId = 0;
  #structElementIdPrefix = `pdfjs_internal_struct_${getUuid()}_`;
  #structElementIds = new Map();
  #structElements = new Map();
  #rawDims;
  #elementsToAddToTextLayer = null;
  #elementsToHideInTextLayer = null;
  #elementsToStealFromTextLayer = null;
  constructor(pdfPage, rawDims) {
    this.#promise = pdfPage.getStructTree();
    this.#rawDims = rawDims;
  }
  async render() {
    if (this.#treePromise) {
      return this.#treePromise;
    }
    const {
      promise,
      resolve,
      reject
    } = Promise.withResolvers();
    this.#treePromise = promise;
    try {
      const tree = await this.#promise;
      this.#collectStructElements(tree);
      this.#collectAnnotations(tree);
      this.#treeDom = this.#walk(tree);
    } catch (ex) {
      reject(ex);
    }
    this.#promise = null;
    this.#treeDom?.classList.add("structTree");
    resolve(this.#treeDom);
    return promise;
  }
  async getAriaAttributes(annotationId, {
    enableLinkOwnership = false
  } = {}) {
    try {
      await this.render();
      const ownership = this.#pendingLinkOwnership.get(annotationId);
      if (ownership && enableLinkOwnership) {
        const {
          element,
          ids
        } = ownership;
        element.removeAttribute("role");
        if (ids.length > 0) {
          this.#elementAttributes.getOrInsertComputed(annotationId, makeMap).set("aria-owns", ids.join(" "));
        }
        this.#pendingLinkOwnership.delete(annotationId);
      }
      return this.#elementAttributes.get(annotationId);
    } catch {}
    return null;
  }
  async getAnnotationIds() {
    try {
      await this.render();
      return this.#annotationIds;
    } catch {}
    return null;
  }
  hide() {
    if (this.#treeDom && !this.#treeDom.hidden) {
      this.#treeDom.hidden = true;
    }
  }
  show() {
    if (this.#treeDom?.hidden) {
      this.#treeDom.hidden = false;
    }
  }
  #collectStructElements(node) {
    if (!node) {
      return;
    }
    if (node.structId) {
      this.#structElements.getOrInsert(node.structId, node);
    }
    for (const child of node.children || []) {
      this.#collectStructElements(child);
    }
  }
  #collectAnnotations(node) {
    if (!node) {
      return;
    }
    if (node.type === "annotation") {
      this.#annotationIds.add(node.id);
      return;
    }
    for (const child of node.children || []) {
      this.#collectAnnotations(child);
    }
  }
  #getStructElementId(structId) {
    return this.#structElementIds.getOrInsertComputed(structId, () => `${this.#structElementIdPrefix}${this.#structElementIds.size}`);
  }
  #getHeaderIds(headers) {
    const result = [],
      visited = new Set(),
      pending = headers.toReversed();
    while (pending.length > 0) {
      const structId = pending.pop();
      if (visited.has(structId)) {
        continue;
      }
      visited.add(structId);
      const header = this.#structElements.get(structId);
      if (header?.role !== "TH") {
        continue;
      }
      result.push(this.#getStructElementId(structId));
      if (header.headers) {
        for (let i = header.headers.length - 1; i >= 0; i--) {
          pending.push(header.headers[i]);
        }
      }
    }
    return result;
  }
  #setAttributes(structElement, htmlElement) {
    const {
      alt,
      colSpan,
      headers,
      id,
      lang,
      rowSpan,
      short,
      structId,
      summary
    } = structElement;
    if (alt !== undefined) {
      let added = false;
      const label = removeNullCharacters(alt);
      for (const child of structElement.children) {
        if (child.type === "annotation") {
          this.#elementAttributes.getOrInsertComputed(child.id, makeMap).set("aria-label", label);
          added = true;
        }
      }
      const role = htmlElement.getAttribute("role") || (htmlElement.localName === "span" ? "generic" : null);
      if (!added && role !== "none") {
        htmlElement.setAttribute(ARIA_ROLES_WITH_PROHIBITED_NAMES.has(role) ? "aria-description" : "aria-label", label);
      }
    }
    if (id !== undefined) {
      htmlElement.setAttribute("aria-owns", id);
    }
    if (structId !== undefined && this.#structElements.get(structId) === structElement) {
      const elementId = this.#getStructElementId(structId);
      if (short !== undefined) {
        const abbreviation = document.createElement("span");
        abbreviation.setAttribute("id", elementId);
        abbreviation.setAttribute("aria-hidden", "true");
        abbreviation.textContent = removeNullCharacters(short);
        htmlElement.append(abbreviation);
      } else {
        htmlElement.setAttribute("id", elementId);
      }
    }
    if (lang !== undefined) {
      htmlElement.setAttribute("lang", removeNullCharacters(lang, true));
    }
    if (rowSpan !== undefined) {
      htmlElement.setAttribute("aria-rowspan", rowSpan);
    }
    if (colSpan !== undefined) {
      htmlElement.setAttribute("aria-colspan", colSpan);
    }
    if (headers?.length > 0) {
      const headerIds = this.#getHeaderIds(headers);
      if (headerIds.length > 0) {
        htmlElement.setAttribute("aria-describedby", headerIds.join(" "));
      }
    }
    if (summary !== undefined) {
      htmlElement.setAttribute("aria-description", removeNullCharacters(summary));
    }
  }
  #addImageInTextLayer(node, element) {
    const {
      alt,
      bbox,
      children
    } = node;
    const child = children?.[0];
    if (!this.#rawDims || !alt || !bbox || child?.type !== "content") {
      return false;
    }
    const {
      id
    } = child;
    if (!id) {
      return false;
    }
    element.setAttribute("aria-owns", id);
    const img = document.createElement("span");
    (this.#elementsToAddToTextLayer ||= new Map()).set(id, img);
    img.setAttribute("role", "img");
    img.setAttribute("aria-label", removeNullCharacters(alt));
    const {
      pageHeight,
      pageX,
      pageY
    } = this.#rawDims;
    const calc = "calc(var(--total-scale-factor) *";
    const {
      style
    } = img;
    style.width = `${calc}${bbox[2] - bbox[0]}px)`;
    style.height = `${calc}${bbox[3] - bbox[1]}px)`;
    style.left = `${calc}${bbox[0] - pageX}px)`;
    style.top = `${calc}${pageHeight - bbox[3] + pageY}px)`;
    return true;
  }
  updateTextLayer() {
    if (this.#elementsToAddToTextLayer) {
      for (const [id, img] of this.#elementsToAddToTextLayer) {
        document.getElementById(id)?.append(img);
      }
      this.#elementsToAddToTextLayer.clear();
      this.#elementsToAddToTextLayer = null;
    }
    if (this.#elementsToHideInTextLayer) {
      for (const id of this.#elementsToHideInTextLayer) {
        const elem = document.getElementById(id);
        if (elem) {
          elem.ariaHidden = true;
        }
      }
      this.#elementsToHideInTextLayer.length = 0;
      this.#elementsToHideInTextLayer = null;
    }
    if (this.#elementsToStealFromTextLayer) {
      for (let i = 0, ii = this.#elementsToStealFromTextLayer.length; i < ii; i += 2) {
        const element = this.#elementsToStealFromTextLayer[i];
        const ids = this.#elementsToStealFromTextLayer[i + 1];
        let textContent = "";
        for (const id of ids) {
          const elem = document.getElementById(id);
          if (elem) {
            textContent += elem.textContent.trim() || "";
            elem.ariaHidden = "true";
          }
        }
        if (textContent) {
          element.textContent = textContent;
        }
      }
      this.#elementsToStealFromTextLayer.length = 0;
      this.#elementsToStealFromTextLayer = null;
    }
  }
  #collectIds(node, ids) {
    if (!node) {
      return;
    }
    if ("id" in node) {
      ids.push(node.id);
    }
    for (const kid of node.children || []) {
      this.#collectIds(kid, ids);
    }
  }
  #walk(node, parentNodes = []) {
    if (!node) {
      return null;
    }
    let element;
    let visitChildren = true;
    if ("role" in node) {
      const {
        role
      } = node;
      if (MathMLElements.has(role)) {
        element = document.createElementNS(MathMLNamespace, role);
        const ids = [];
        (this.#elementsToStealFromTextLayer ||= []).push(element, ids);
        for (const {
          type,
          id
        } of node.children || []) {
          if (type === "content" && id) {
            ids.push(id);
          }
        }
      } else {
        element = document.createElement("span");
      }
      const match = role.match(HEADING_PATTERN);
      if (match) {
        element.setAttribute("role", "heading");
        element.setAttribute("aria-level", match[1]);
      } else if (PDF_ROLE_TO_HTML_ROLE[role]) {
        let htmlRole = PDF_ROLE_TO_HTML_ROLE[role];
        if (role === "TH") {
          if (node.scope === "Row") {
            htmlRole = "rowheader";
          } else if (node.scope === "Column") {
            htmlRole = "columnheader";
          } else if (parentNodes.at(-1)?.role === "TR" && parentNodes.at(-2)?.role === "TBody") {
            htmlRole = "rowheader";
          }
        } else if (role === "Caption") {
          const parentRole = parentNodes.at(-1)?.role;
          if (parentRole !== "Table" && parentRole !== "Figure") {
            htmlRole = null;
          }
        }
        if (htmlRole) {
          element.setAttribute("role", htmlRole);
        }
      }
      if (role === "Figure" && this.#addImageInTextLayer(node, element)) {
        return element;
      }
      if (role === "Formula") {
        if (node.mathML && MathMLSanitizer.sanitizer) {
          visitChildren = false;
          element.setHTML(node.mathML, {
            sanitizer: MathMLSanitizer.sanitizer
          });
          this.#collectIds(node, this.#elementsToHideInTextLayer ||= []);
          delete node.alt;
        }
        if (!node.mathML && node.children.length === 1 && node.children[0].role !== "math") {
          element = document.createElementNS(MathMLNamespace, "math");
          delete node.alt;
        }
      }
    }
    element ||= document.createElement("span");
    this.#setAttributes(node, element);
    if (node.children) {
      if (node.children.length === 1 && !("role" in node.children[0]) && "id" in node.children[0] && element.getAttribute("role") !== "none") {
        this.#setAttributes(node.children[0], element);
      } else if (visitChildren) {
        parentNodes.push(node);
        for (const kid of node.children) {
          element.append(this.#walk(kid, parentNodes));
        }
        parentNodes.pop();
      }
    }
    if (node.role === "Link") {
      const annotations = node.children?.filter(child => child.type === "annotation");
      if (annotations?.length === 1) {
        const annotation = annotations[0];
        const ids = [];
        for (const child of element.children) {
          if (child.getAttribute("aria-owns") === annotation.id) {
            continue;
          }
          child.id ||= `${this.#structElementIdPrefix}link_${this.#linkTextId++}`;
          ids.push(child.id);
        }
        this.#pendingLinkOwnership.set(annotation.id, {
          element,
          ids
        });
      }
    }
    return element;
  }
}

;// ./web/text_accessibility.js

class TextAccessibilityManager {
  #enabled = false;
  #textChildren = null;
  #textNodes = new Map();
  #waitingElements = new Map();
  setTextMapping(textDivs) {
    this.#textChildren = textDivs;
  }
  static #compareElementPositions(e1, e2) {
    const rect1 = e1.getBoundingClientRect();
    const rect2 = e2.getBoundingClientRect();
    if (rect1.width === 0 && rect1.height === 0) {
      return +1;
    }
    if (rect2.width === 0 && rect2.height === 0) {
      return -1;
    }
    const top1 = rect1.y;
    const bot1 = rect1.y + rect1.height;
    const mid1 = rect1.y + rect1.height / 2;
    const top2 = rect2.y;
    const bot2 = rect2.y + rect2.height;
    const mid2 = rect2.y + rect2.height / 2;
    if (mid1 <= top2 && mid2 >= bot1) {
      return -1;
    }
    if (mid2 <= top1 && mid1 >= bot2) {
      return +1;
    }
    const centerX1 = rect1.x + rect1.width / 2;
    const centerX2 = rect2.x + rect2.width / 2;
    return centerX1 - centerX2;
  }
  enable() {
    if (this.#enabled) {
      throw new Error("TextAccessibilityManager is already enabled.");
    }
    if (!this.#textChildren) {
      throw new Error("Text divs and strings have not been set.");
    }
    this.#enabled = true;
    this.#textChildren = this.#textChildren.slice();
    this.#textChildren.sort(TextAccessibilityManager.#compareElementPositions);
    if (this.#textNodes.size > 0) {
      const textChildren = this.#textChildren;
      for (const [id, nodeIndex] of this.#textNodes) {
        const element = document.getElementById(id);
        if (!element) {
          this.#textNodes.delete(id);
          continue;
        }
        this.#addIdToAriaOwns(id, textChildren[nodeIndex]);
      }
    }
    for (const [element, isRemovable] of this.#waitingElements) {
      this.addPointerInTextLayer(element, isRemovable);
    }
    this.#waitingElements.clear();
  }
  disable() {
    if (!this.#enabled) {
      return;
    }
    this.#waitingElements.clear();
    this.#textChildren = null;
    this.#enabled = false;
  }
  removePointerInTextLayer(element) {
    if (!this.#enabled) {
      this.#waitingElements.delete(element);
      return;
    }
    const children = this.#textChildren;
    if (!children?.length) {
      return;
    }
    const {
      id
    } = element;
    const nodeIndex = this.#textNodes.get(id);
    if (nodeIndex === undefined) {
      return;
    }
    const node = children[nodeIndex];
    this.#textNodes.delete(id);
    let owns = node.getAttribute("aria-owns");
    if (owns?.includes(id)) {
      owns = owns.split(" ").filter(x => x !== id).join(" ");
      if (owns) {
        node.setAttribute("aria-owns", owns);
      } else {
        node.removeAttribute("aria-owns");
        node.setAttribute("role", "presentation");
      }
    }
  }
  #addIdToAriaOwns(id, node) {
    const owns = node.getAttribute("aria-owns");
    if (!owns?.includes(id)) {
      node.setAttribute("aria-owns", owns ? `${owns} ${id}` : id);
    }
    node.removeAttribute("role");
  }
  addPointerInTextLayer(element, isRemovable) {
    const {
      id
    } = element;
    if (!id) {
      return null;
    }
    if (!this.#enabled) {
      this.#waitingElements.set(element, isRemovable);
      return null;
    }
    if (isRemovable) {
      this.removePointerInTextLayer(element);
    }
    const children = this.#textChildren;
    if (!children?.length) {
      return null;
    }
    const index = binarySearchFirstItem(children, node => TextAccessibilityManager.#compareElementPositions(element, node) < 0);
    const nodeIndex = Math.max(0, index - 1);
    const child = children[nodeIndex];
    this.#addIdToAriaOwns(id, child);
    this.#textNodes.set(id, nodeIndex);
    const parent = child.parentNode;
    return parent?.classList.contains("markedContent") ? parent.id : null;
  }
  moveElementInDOM(container, element, contentElement, isRemovable) {
    const id = this.addPointerInTextLayer(contentElement, isRemovable);
    if (!container.hasChildNodes()) {
      container.append(element);
      return id;
    }
    const children = Array.from(container.childNodes).filter(node => node !== element);
    if (children.length === 0) {
      return id;
    }
    const index = binarySearchFirstItem(children, node => TextAccessibilityManager.#compareElementPositions(element, node) < 0);
    if (index === 0) {
      children[0].before(element);
    } else {
      children[index - 1].after(element);
    }
    return id;
  }
}

;// ./web/text_highlighter.js

class TextHighlighter {
  #eventAC = null;
  constructor({
    findController,
    eventBus,
    pageIndex
  }) {
    this.findController = findController;
    this.matches = [];
    this.eventBus = eventBus;
    this.pageIdx = pageIndex;
    this.textDivs = null;
    this.textContentItemsStr = null;
    this.enabled = false;
  }
  setTextMapping(divs, texts) {
    this.textDivs = divs;
    this.textContentItemsStr = texts;
  }
  enable() {
    if (!this.textDivs || !this.textContentItemsStr) {
      throw new Error("Text divs and strings have not been set.");
    }
    if (this.enabled) {
      throw new Error("TextHighlighter is already enabled.");
    }
    this.enabled = true;
    if (!this.#eventAC) {
      this.#eventAC = new AbortController();
      this.eventBus.on("updatetextlayermatches", evt => {
        if (evt.pageIndex === this.pageIdx || evt.pageIndex === -1) {
          this._updateMatches();
        }
      }, {
        signal: this.#eventAC.signal,
        ...internalOpt
      });
    }
    this._updateMatches();
  }
  disable() {
    if (!this.enabled) {
      return;
    }
    this.enabled = false;
    this.#eventAC?.abort();
    this.#eventAC = null;
    this._updateMatches(true);
  }
  _convertMatches(matches, matchesLength) {
    if (!matches) {
      return [];
    }
    const {
      textContentItemsStr
    } = this;
    let i = 0,
      iIndex = 0;
    const end = textContentItemsStr.length - 1;
    const result = [];
    for (let m = 0, mm = matches.length; m < mm; m++) {
      let matchIdx = matches[m];
      while (i !== end && matchIdx >= iIndex + textContentItemsStr[i].length) {
        iIndex += textContentItemsStr[i].length;
        i++;
      }
      if (i === textContentItemsStr.length) {
        console.error("Could not find a matching mapping");
      }
      const match = {
        begin: {
          divIdx: i,
          offset: matchIdx - iIndex
        }
      };
      matchIdx += matchesLength[m];
      while (i !== end && matchIdx > iIndex + textContentItemsStr[i].length) {
        iIndex += textContentItemsStr[i].length;
        i++;
      }
      match.end = {
        divIdx: i,
        offset: matchIdx - iIndex
      };
      result.push(match);
    }
    return result;
  }
  _renderMatches(matches) {
    if (matches.length === 0) {
      return;
    }
    const {
      findController,
      pageIdx
    } = this;
    const {
      textContentItemsStr,
      textDivs
    } = this;
    const isSelectedPage = pageIdx === findController.selected.pageIdx;
    const selectedMatchIdx = findController.selected.matchIdx;
    const highlightAll = findController.state.highlightAll;
    let prevEnd = null;
    const infinity = {
      divIdx: -1,
      offset: undefined
    };
    function beginText(begin, className) {
      const divIdx = begin.divIdx;
      textDivs[divIdx].textContent = "";
      return appendTextToDiv(divIdx, 0, begin.offset, className);
    }
    function appendTextToDiv(divIdx, fromOffset, toOffset, className) {
      let div = textDivs[divIdx];
      if (div.nodeType === Node.TEXT_NODE) {
        const span = document.createElement("span");
        div.before(span);
        span.append(div);
        textDivs[divIdx] = span;
        div = span;
      }
      const content = textContentItemsStr[divIdx].substring(fromOffset, toOffset);
      const node = document.createTextNode(content);
      if (className) {
        const span = document.createElement("span");
        span.className = `${className} appended`;
        span.append(node);
        div.append(span);
        return className.includes("selected") ? span : null;
      }
      div.append(node);
      return 0;
    }
    let i0 = selectedMatchIdx,
      i1 = i0 + 1;
    if (highlightAll) {
      i0 = 0;
      i1 = matches.length;
    } else if (!isSelectedPage) {
      return;
    }
    let lastDivIdx = -1;
    let lastOffset = -1;
    for (let i = i0; i < i1; i++) {
      const match = matches[i];
      const begin = match.begin;
      if (begin.divIdx === lastDivIdx && begin.offset === lastOffset) {
        continue;
      }
      lastDivIdx = begin.divIdx;
      lastOffset = begin.offset;
      const end = match.end;
      const isSelected = isSelectedPage && i === selectedMatchIdx;
      const highlightSuffix = isSelected ? " selected" : "";
      let selectedSpan = null;
      if (!prevEnd || begin.divIdx !== prevEnd.divIdx) {
        if (prevEnd !== null) {
          appendTextToDiv(prevEnd.divIdx, prevEnd.offset, infinity.offset);
        }
        beginText(begin);
      } else {
        appendTextToDiv(prevEnd.divIdx, prevEnd.offset, begin.offset);
      }
      if (begin.divIdx === end.divIdx) {
        selectedSpan = appendTextToDiv(begin.divIdx, begin.offset, end.offset, "highlight" + highlightSuffix);
      } else {
        selectedSpan = appendTextToDiv(begin.divIdx, begin.offset, infinity.offset, "highlight begin" + highlightSuffix);
        for (let n0 = begin.divIdx + 1, n1 = end.divIdx; n0 < n1; n0++) {
          textDivs[n0].className = "highlight middle" + highlightSuffix;
        }
        beginText(end, "highlight end" + highlightSuffix);
      }
      prevEnd = end;
      if (isSelected) {
        findController.scrollMatchIntoView({
          element: selectedSpan,
          pageIndex: pageIdx,
          matchIndex: selectedMatchIdx
        });
      }
    }
    if (prevEnd) {
      appendTextToDiv(prevEnd.divIdx, prevEnd.offset, infinity.offset);
    }
  }
  _updateMatches(reset = false) {
    if (!this.enabled && !reset) {
      return;
    }
    const {
      findController,
      matches,
      pageIdx
    } = this;
    const {
      textContentItemsStr,
      textDivs
    } = this;
    let clearedUntilDivIdx = -1;
    for (const match of matches) {
      const begin = Math.max(clearedUntilDivIdx, match.begin.divIdx);
      for (let n = begin, end = match.end.divIdx; n <= end; n++) {
        const div = textDivs[n];
        div.textContent = textContentItemsStr[n];
        div.className = "";
      }
      clearedUntilDivIdx = match.end.divIdx + 1;
    }
    if (!findController?.highlightMatches || reset) {
      return;
    }
    const pageMatches = findController.pageMatches[pageIdx] || null;
    const pageMatchesLength = findController.pageMatchesLength[pageIdx] || null;
    this.matches = this._convertMatches(pageMatches, pageMatchesLength);
    this._renderMatches(this.matches);
  }
}

;// ./web/text_layer_builder.js


class TextLayerBuilder {
  #abortSignal = null;
  #enablePermissions = false;
  #onAppend = null;
  #renderingDone = false;
  #textLayer = null;
  static #textLayers = new Map();
  static #selectionChangeAC = null;
  constructor({
    pdfPage,
    highlighter = null,
    accessibilityManager = null,
    enablePermissions = false,
    onAppend = null,
    abortSignal = null
  }) {
    this.pdfPage = pdfPage;
    this.highlighter = highlighter;
    this.accessibilityManager = accessibilityManager;
    this.#enablePermissions = enablePermissions === true;
    this.#onAppend = onAppend;
    this.#abortSignal = abortSignal;
    this.div = document.createElement("div");
    this.div.tabIndex = 0;
    this.div.className = "textLayer";
  }
  async render({
    viewport,
    images,
    textContentParams = null
  }) {
    if (this.#renderingDone && this.#textLayer) {
      this.#textLayer.update({
        viewport
      });
      this.show();
      return;
    }
    this.cancel();
    this.#textLayer = new TextLayer({
      textContentSource: this.pdfPage.streamTextContent(textContentParams || {
        includeMarkedContent: true,
        disableNormalization: true
      }),
      images,
      container: this.div,
      viewport
    });
    const {
      textDivs,
      textContentItemsStr
    } = this.#textLayer;
    this.highlighter?.setTextMapping(textDivs, textContentItemsStr);
    this.accessibilityManager?.setTextMapping(textDivs);
    await this.#textLayer.render();
    this.#renderingDone = true;
    const endOfContent = document.createElement("div");
    endOfContent.className = "endOfContent";
    this.div.append(endOfContent);
    this.#bindMouse(endOfContent);
    this.#onAppend?.(this.div);
    this.highlighter?.enable();
    this.accessibilityManager?.enable();
  }
  hide() {
    if (!this.div.hidden && this.#renderingDone) {
      this.highlighter?.disable();
      this.div.hidden = true;
    }
  }
  show() {
    if (this.div.hidden && this.#renderingDone) {
      this.div.hidden = false;
      this.highlighter?.enable();
    }
  }
  cancel() {
    this.#textLayer?.cancel();
    this.#textLayer = null;
    this.#renderingDone = false;
    this.div.replaceChildren();
    this.highlighter?.disable();
    this.accessibilityManager?.disable();
    TextLayerBuilder.#removeGlobalSelectionListener(this.div);
  }
  #bindMouse(end) {
    const {
      div
    } = this;
    const abortSignal = this.#abortSignal;
    const opts = abortSignal ? {
      signal: abortSignal
    } : null;
    div.addEventListener("mousedown", () => {
      div.classList.add("selecting");
    }, opts);
    div.addEventListener("copy", event => {
      if (!this.#enablePermissions) {
        const selection = document.getSelection();
        event.clipboardData.setData("text/plain", removeNullCharacters(normalizeUnicode(selection.toString())));
      }
      stopEvent(event);
    }, opts);
    TextLayerBuilder.#textLayers.set(div, end);
    TextLayerBuilder.#enableGlobalSelectionListener(abortSignal);
  }
  static #removeGlobalSelectionListener(textLayerDiv) {
    this.#textLayers.delete(textLayerDiv);
    if (this.#textLayers.size === 0) {
      this.#selectionChangeAC?.abort();
      this.#selectionChangeAC = null;
    }
  }
  static #enableGlobalSelectionListener(globalAbortSignal) {
    if (this.#selectionChangeAC) {
      return;
    }
    this.#selectionChangeAC = new AbortController();
    const signal = globalAbortSignal ? AbortSignal.any([this.#selectionChangeAC.signal, globalAbortSignal]) : this.#selectionChangeAC.signal;
    const reset = (end, textLayer) => {
      textLayer.append(end);
      end.style.width = "";
      end.style.height = "";
      textLayer.classList.remove("selecting");
    };
    let isPointerDown = false;
    document.addEventListener("pointerdown", () => {
      isPointerDown = true;
    }, {
      signal
    });
    document.addEventListener("pointerup", () => {
      isPointerDown = false;
      this.#textLayers.forEach(reset);
    }, {
      signal
    });
    window.addEventListener("blur", () => {
      isPointerDown = false;
      this.#textLayers.forEach(reset);
    }, {
      signal
    });
    document.addEventListener("keyup", () => {
      if (!isPointerDown) {
        this.#textLayers.forEach(reset);
      }
    }, {
      signal
    });
    var isFirefoxOrModernChromium, prevRange;
    document.addEventListener("selectionchange", () => {
      const selection = document.getSelection();
      if (selection.rangeCount === 0) {
        this.#textLayers.forEach(reset);
        return;
      }
      const activeTextLayers = new Set();
      for (let i = 0; i < selection.rangeCount; i++) {
        const range = selection.getRangeAt(i);
        if (range.collapsed && !isPointerDown) {
          continue;
        }
        for (const textLayerDiv of this.#textLayers.keys()) {
          if (!activeTextLayers.has(textLayerDiv) && range.intersectsNode(textLayerDiv)) {
            activeTextLayers.add(textLayerDiv);
          }
        }
      }
      for (const [textLayerDiv, endDiv] of this.#textLayers) {
        if (activeTextLayers.has(textLayerDiv)) {
          textLayerDiv.classList.add("selecting");
        } else {
          reset(endDiv, textLayerDiv);
        }
      }
      if (isFirefoxOrModernChromium === undefined) {
        isFirefoxOrModernChromium = getComputedStyle(this.#textLayers.values().next().value).getPropertyValue("-moz-user-select") === "none";
        if (!isFirefoxOrModernChromium) {
          const chromiumVersion = navigator.userAgentData ? navigator.userAgentData.brands.find(({
            brand
          }) => brand === "Chromium")?.version : /\bChrome\/(\d+)\b/.exec(navigator.userAgent)?.[1];
          isFirefoxOrModernChromium = !!chromiumVersion && parseInt(chromiumVersion, 10) >= 148;
        }
      }
      if (isFirefoxOrModernChromium) {
        return;
      }
      const range = selection.getRangeAt(0);
      const modifyStart = prevRange && (range.compareBoundaryPoints(Range.END_TO_END, prevRange) === 0 || range.compareBoundaryPoints(Range.START_TO_END, prevRange) === 0);
      let anchor = modifyStart ? range.startContainer : range.endContainer;
      if (anchor.nodeType === Node.TEXT_NODE) {
        anchor = anchor.parentNode;
      }
      if (anchor.classList?.contains("highlight")) {
        anchor = anchor.parentNode;
      }
      if (!modifyStart && range.endOffset === 0) {
        do {
          while (!anchor.previousSibling) {
            anchor = anchor.parentNode;
          }
          anchor = anchor.previousSibling;
        } while (!anchor.childNodes.length);
      }
      const parentTextLayer = anchor.parentElement?.closest(".textLayer");
      const endDiv = this.#textLayers.get(parentTextLayer);
      if (endDiv) {
        endDiv.style.width = parentTextLayer.style.width;
        endDiv.style.height = parentTextLayer.style.height;
        endDiv.style.userSelect = "text";
        anchor.parentElement.insertBefore(endDiv, modifyStart ? anchor : anchor.nextSibling);
      }
      prevRange = range.cloneRange();
    }, {
      signal
    });
  }
}

;// ./web/pdf_page_view.js

















const DEFAULT_LAYER_PROPERTIES = null;
const LAYERS_ORDER = new Map([["canvasWrapper", 0], ["textLayer", 1], ["annotationLayer", 2], ["annotationEditorLayer", 3], ["xfaLayer", 3]]);
class PDFPageView extends BasePDFPageView {
  #abortSignal = null;
  #annotationMode = AnnotationMode.ENABLE_FORMS;
  #canvasWrapper = null;
  #commentManager = null;
  #enableAutoLinking = true;
  #hasRestrictedScaling = false;
  #isEditing = false;
  #layerProperties = null;
  #needsRestrictedScaling = false;
  #originalViewport = null;
  #previousRotation = null;
  #scaleRoundX = 1;
  #scaleRoundY = 1;
  #textLayerMode = TextLayerMode.ENABLE;
  #userUnit = 1;
  #useThumbnailCanvas = {
    directDrawing: true,
    initialOptionalContent: true,
    regularAnnotations: true
  };
  #layers = [null, null, null, null];
  constructor(options) {
    super(options);
    const {
      container,
      defaultViewport
    } = options;
    this.renderingId = "page" + this.id;
    this.#layerProperties = options.layerProperties || DEFAULT_LAYER_PROPERTIES;
    this.#abortSignal = options.abortSignal || null;
    this.pdfPage = null;
    this.pageLabel = null;
    this.rotation = 0;
    this.scale = options.scale || (/* inlined export .DEFAULT_SCALE */1);
    this.viewport = defaultViewport;
    this.pdfPageRotate = defaultViewport.rotation;
    this._optionalContentConfigPromise = options.optionalContentConfigPromise || null;
    this.#textLayerMode = options.textLayerMode ?? TextLayerMode.ENABLE;
    this.#annotationMode = options.annotationMode ?? AnnotationMode.ENABLE_FORMS;
    this.imageResourcesPath = options.imageResourcesPath || "";
    this.enableDetailCanvas = options.enableDetailCanvas ?? true;
    this.maxCanvasPixels = options.maxCanvasPixels ?? AppOptions.get("maxCanvasPixels");
    this.maxCanvasDim = options.maxCanvasDim || AppOptions.get("maxCanvasDim");
    this.capCanvasAreaFactor = options.capCanvasAreaFactor ?? AppOptions.get("capCanvasAreaFactor");
    this.#enableAutoLinking = options.enableAutoLinking !== false;
    this.#commentManager = options.commentManager || null;
    this.l10n = options.l10n;
    this.l10n ||= new genericl10n_GenericL10n();
    this._isStandalone = !this.renderingQueue?.hasViewer();
    this._container = container;
    this._annotationCanvasMap = null;
    this.annotationLayer = null;
    this.annotationEditorLayer = null;
    this.textLayer = null;
    this.xfaLayer = null;
    this.structTreeLayer = null;
    this.drawLayer = null;
    this.detailView = null;
    const div = document.createElement("div");
    div.className = "page";
    div.setAttribute("data-page-number", this.id);
    div.setAttribute("role", "region");
    div.setAttribute("data-l10n-id", "pdfjs-page-landmark");
    div.setAttribute("data-l10n-args", JSON.stringify({
      page: this.id
    }));
    this.div = div;
    this.#setDimensions();
    container?.append(div);
    if (this._isStandalone) {
      container?.style.setProperty("--scale-factor", this.scale * PixelsPerInch.PDF_TO_CSS_UNITS);
      if (this.pageColors?.background) {
        container?.style.setProperty("--page-bg-color", this.pageColors.background);
      }
      const {
        optionalContentConfigPromise
      } = options;
      if (optionalContentConfigPromise) {
        optionalContentConfigPromise.then(optionalContentConfig => {
          if (optionalContentConfigPromise !== this._optionalContentConfigPromise) {
            return;
          }
          this.#useThumbnailCanvas.initialOptionalContent = optionalContentConfig.hasInitialVisibility;
        });
      }
      if (!options.l10n) {
        this.l10n.translate(this.div);
      }
    }
  }
  clone(id) {
    const clone = new PDFPageView({
      container: null,
      eventBus: this.eventBus,
      pagesColors: this.pageColors,
      renderingQueue: this.renderingQueue,
      enableOptimizedPartialRendering: this.enableOptimizedPartialRendering,
      minDurationToUpdateCanvas: this.minDurationToUpdateCanvas,
      defaultViewport: this.viewport,
      id,
      layerProperties: this.#layerProperties,
      abortSignal: this.#abortSignal,
      scale: this.scale,
      optionalContentConfigPromise: this._optionalContentConfigPromise,
      textLayerMode: this.#textLayerMode,
      annotationMode: this.#annotationMode,
      imageResourcesPath: this.imageResourcesPath,
      enableDetailCanvas: this.enableDetailCanvas,
      maxCanvasPixels: this.maxCanvasPixels,
      maxCanvasDim: this.maxCanvasDim,
      capCanvasAreaFactor: this.capCanvasAreaFactor,
      enableAutoLinking: this.#enableAutoLinking,
      commentManager: this.#commentManager,
      l10n: this.l10n
    });
    clone.setPdfPage(this.pdfPage.clone(id - 1));
    return clone;
  }
  #addLayer(div, name) {
    const pos = LAYERS_ORDER.get(name);
    const oldDiv = this.#layers[pos];
    this.#layers[pos] = div;
    if (oldDiv) {
      oldDiv.replaceWith(div);
      return;
    }
    for (let i = pos - 1; i >= 0; i--) {
      const layer = this.#layers[i];
      if (layer) {
        layer.after(div);
        return;
      }
    }
    this.div.prepend(div);
  }
  #setDimensions() {
    const {
      div,
      viewport
    } = this;
    if (viewport.userUnit !== this.#userUnit) {
      if (viewport.userUnit !== 1) {
        div.style.setProperty("--user-unit", viewport.userUnit);
      } else {
        div.style.removeProperty("--user-unit");
      }
      this.#userUnit = viewport.userUnit;
    }
    if (this.pdfPage) {
      if (this.#previousRotation === viewport.rotation) {
        return;
      }
      this.#previousRotation = viewport.rotation;
    }
    setLayerDimensions(div, viewport, true, false);
  }
  updatePageNumber(newPageNumber) {
    const oldPageNumber = this.id;
    if (oldPageNumber !== newPageNumber) {
      this.id = newPageNumber;
      this.renderingId = `page${newPageNumber}`;
      if (this.pdfPage) {
        this.pdfPage.pageNumber = newPageNumber;
      }
      this.setPageLabel(this.pageLabel);
      const {
        div
      } = this;
      div.setAttribute("data-page-number", newPageNumber);
      div.setAttribute("data-l10n-args", JSON.stringify({
        page: newPageNumber
      }));
      this._textHighlighter.pageIdx = newPageNumber - 1;
    }
    this.#layerProperties.annotationEditorUIManager?.updatePageIndex(oldPageNumber - 1, newPageNumber - 1);
  }
  setPdfPage(pdfPage) {
    if (this._isStandalone && (this.pageColors?.foreground === "CanvasText" || this.pageColors?.background === "Canvas")) {
      this._container?.style.setProperty("--hcm-highlight-filter", pdfPage.filterFactory.addHighlightHCMFilter("highlight", "CanvasText", "Canvas", "HighlightText", "Highlight"));
      this._container?.style.setProperty("--hcm-highlight-selected-filter", pdfPage.filterFactory.addHighlightHCMFilter("highlight_selected", "CanvasText", "Canvas", "HighlightText", "Highlight"));
    }
    this.pdfPage = pdfPage;
    this.pdfPageRotate = pdfPage.rotate;
    const totalRotation = (this.rotation + this.pdfPageRotate) % 360;
    this.viewport = pdfPage.getViewport({
      scale: this.scale * PixelsPerInch.PDF_TO_CSS_UNITS,
      rotation: totalRotation
    });
    this.#setDimensions();
    this.reset();
  }
  destroy() {
    this.reset();
    this.pdfPage?.cleanup();
  }
  deleteMe(isCut) {
    if (isCut) {
      this.div.remove();
      return;
    }
    this.destroy();
    this.#layerProperties.annotationEditorUIManager?.deletePage(this.id);
  }
  hasEditableAnnotations() {
    return !!this.annotationLayer?.hasEditableAnnotations();
  }
  get _textHighlighter() {
    return shadow(this, "_textHighlighter", new TextHighlighter({
      pageIndex: this.id - 1,
      eventBus: this.eventBus,
      findController: this.#layerProperties.findController
    }));
  }
  #dispatchLayerRendered(name, error) {
    this.eventBus.dispatch(name, {
      source: this,
      pageNumber: this.id,
      error
    });
  }
  async #renderAnnotationLayer(textLayerPromise = null) {
    const {
      annotationLayer,
      textLayer
    } = this;
    let error = null;
    try {
      await this.annotationLayer.render({
        viewport: this.viewport,
        intent: "display",
        structTreeLayer: this.structTreeLayer,
        optionalContentConfigPromise: this._optionalContentConfigPromise
      });
    } catch (ex) {
      console.error("#renderAnnotationLayer:", ex);
      error = ex;
    } finally {
      this.#dispatchLayerRendered("annotationlayerrendered", error);
    }
    if (this.#enableAutoLinking && textLayerPromise && !annotationLayer.linksInjected) {
      this.#injectLinkAnnotations(textLayerPromise, annotationLayer, textLayer);
    }
  }
  _refreshAnnotationLayer() {
    if (this._annotationCanvasMap?.size) {
      this.annotationLayer?.refreshCanvases();
    }
  }
  async #renderAnnotationEditorLayer() {
    let error = null;
    try {
      await this.annotationEditorLayer.render({
        viewport: this.viewport,
        intent: "display"
      });
    } catch (ex) {
      console.error("#renderAnnotationEditorLayer:", ex);
      error = ex;
    } finally {
      this.#dispatchLayerRendered("annotationeditorlayerrendered", error);
    }
  }
  async #renderDrawLayer() {
    try {
      await this.drawLayer.render({
        intent: "display"
      });
    } catch (ex) {
      console.error("#renderDrawLayer:", ex);
    }
  }
  async #renderXfaLayer() {
    let error = null;
    try {
      const result = await this.xfaLayer.render({
        viewport: this.viewport,
        intent: "display"
      });
      if (result?.textDivs && this._textHighlighter) {
        this.#buildXfaTextContentItems(result.textDivs);
      }
    } catch (ex) {
      console.error("#renderXfaLayer:", ex);
      error = ex;
    } finally {
      if (this.xfaLayer?.div) {
        this.l10n.pause();
        this.#addLayer(this.xfaLayer.div, "xfaLayer");
        this.l10n.resume();
      }
      this.#dispatchLayerRendered("xfalayerrendered", error);
    }
  }
  async #renderTextLayer() {
    let error = null;
    try {
      await this.textLayer.render({
        viewport: this.viewport,
        images: this.imageCoordinates ? new TextLayerImages(this.imagesRightClickMinSize, this.imageCoordinates, this.viewport, () => this.canvas) : null
      });
    } catch (ex) {
      if (ex instanceof AbortException) {
        return true;
      }
      console.error("#renderTextLayer:", ex);
      error = ex;
    }
    this.#dispatchLayerRendered("textlayerrendered", error);
    this.#renderStructTreeLayer();
    return false;
  }
  async #renderStructTreeLayer() {
    const treeDom = await this.structTreeLayer?.render();
    if (treeDom) {
      this.l10n.pause();
      this.structTreeLayer?.updateTextLayer();
      if (this.canvas && treeDom.parentNode !== this.canvas) {
        this.canvas.append(treeDom);
      }
      this.l10n.resume();
    }
    this.structTreeLayer?.show();
  }
  async #buildXfaTextContentItems(textDivs) {
    const text = await this.pdfPage.getTextContent();
    const items = [];
    for (const item of text.items) {
      items.push(item.str);
    }
    this._textHighlighter.setTextMapping(textDivs, items);
    this._textHighlighter.enable();
  }
  async #injectLinkAnnotations(textLayerPromise, annotationLayer, textLayer) {
    let error = null;
    try {
      const textLayerAborted = await textLayerPromise;
      if (textLayerAborted || annotationLayer !== this.annotationLayer || textLayer !== this.textLayer || annotationLayer.linksInjected) {
        return;
      }
      await annotationLayer.injectLinkAnnotations(Autolinker.processLinks(this));
    } catch (ex) {
      console.error("#injectLinkAnnotations:", ex);
      error = ex;
    }
    this.#dispatchLayerRendered("linkannotationsadded", error);
  }
  _resetCanvas() {
    super._resetCanvas();
    this.#originalViewport = null;
  }
  reset({
    keepAnnotationLayer = false,
    keepAnnotationEditorLayer = false,
    keepXfaLayer = false,
    keepTextLayer = false,
    keepCanvasWrapper = false,
    preserveDetailViewState = false
  } = {}) {
    const keepPdfBugGroups = this.pdfPage?._pdfBug ?? false;
    this.cancelRendering({
      keepAnnotationLayer,
      keepAnnotationEditorLayer,
      keepXfaLayer,
      keepTextLayer
    });
    this.renderingState = RenderingStates.INITIAL;
    const div = this.div;
    const childNodes = div.childNodes,
      annotationLayerNode = keepAnnotationLayer && this.annotationLayer?.div || null,
      annotationEditorLayerNode = keepAnnotationEditorLayer && this.annotationEditorLayer?.div || null,
      xfaLayerNode = keepXfaLayer && this.xfaLayer?.div || null,
      textLayerNode = keepTextLayer && this.textLayer?.div || null,
      canvasWrapperNode = keepCanvasWrapper && this.#canvasWrapper || null;
    for (let i = childNodes.length - 1; i >= 0; i--) {
      const node = childNodes[i];
      switch (node) {
        case annotationLayerNode:
        case annotationEditorLayerNode:
        case xfaLayerNode:
        case textLayerNode:
        case canvasWrapperNode:
          continue;
      }
      if (keepPdfBugGroups && node.classList.contains("pdfBugGroupsLayer")) {
        continue;
      }
      node.remove();
      const layerIndex = this.#layers.indexOf(node);
      if (layerIndex >= 0) {
        this.#layers[layerIndex] = null;
      }
    }
    div.removeAttribute("data-loaded");
    if (annotationLayerNode) {
      this.annotationLayer.hide();
    }
    if (annotationEditorLayerNode) {
      this.annotationEditorLayer.hide();
    }
    if (xfaLayerNode) {
      this.xfaLayer.hide();
    }
    if (textLayerNode) {
      this.textLayer.hide();
    }
    this.structTreeLayer?.hide();
    if (!keepCanvasWrapper && this.#canvasWrapper) {
      this.#canvasWrapper = null;
      this._resetCanvas();
    }
    if (!preserveDetailViewState) {
      this.detailView?.reset({
        keepCanvas: keepCanvasWrapper
      });
      if (!keepCanvasWrapper) {
        this.detailView = null;
      }
    }
  }
  toggleEditingMode(isEditing) {
    this.#isEditing = isEditing;
    if (!this.hasEditableAnnotations()) {
      return;
    }
    this.reset({
      keepAnnotationLayer: true,
      keepAnnotationEditorLayer: true,
      keepXfaLayer: true,
      keepTextLayer: true,
      keepCanvasWrapper: true
    });
  }
  updateVisibleArea(visibleArea) {
    if (this.enableDetailCanvas) {
      if (this.#needsRestrictedScaling && this.maxCanvasPixels > 0 && visibleArea) {
        this.detailView ??= new PDFPageDetailView({
          pageView: this,
          enableOptimizedPartialRendering: this.enableOptimizedPartialRendering,
          imagesRightClickMinSize: -1
        });
        this.detailView.update({
          visibleArea
        });
      } else if (this.detailView) {
        this.detailView.reset();
        this.detailView = null;
      }
    }
  }
  update({
    scale = 0,
    rotation = null,
    optionalContentConfigPromise = null,
    drawingDelay = -1
  }) {
    this.scale = scale || this.scale;
    if (typeof rotation === "number") {
      this.rotation = rotation;
    }
    if (optionalContentConfigPromise instanceof Promise) {
      this._optionalContentConfigPromise = optionalContentConfigPromise;
      optionalContentConfigPromise.then(optionalContentConfig => {
        if (optionalContentConfigPromise !== this._optionalContentConfigPromise) {
          return;
        }
        this.#useThumbnailCanvas.initialOptionalContent = optionalContentConfig.hasInitialVisibility;
      });
    }
    this.#useThumbnailCanvas.directDrawing = true;
    const totalRotation = (this.rotation + this.pdfPageRotate) % 360;
    this.viewport = this.viewport.clone({
      scale: this.scale * PixelsPerInch.PDF_TO_CSS_UNITS,
      rotation: totalRotation
    });
    this.#setDimensions();
    if (this._isStandalone) {
      this._container?.style.setProperty("--scale-factor", this.viewport.scale);
    }
    this.#computeScale();
    if (this.canvas) {
      const onlyCssZoom = this.#hasRestrictedScaling && this.#needsRestrictedScaling;
      const postponeDrawing = drawingDelay >= 0 && drawingDelay < 1000;
      if (postponeDrawing || onlyCssZoom) {
        if (postponeDrawing && !onlyCssZoom && this.renderingState !== RenderingStates.FINISHED) {
          this.cancelRendering({
            keepAnnotationLayer: true,
            keepAnnotationEditorLayer: true,
            keepXfaLayer: true,
            keepTextLayer: true,
            cancelExtraDelay: drawingDelay
          });
          this.renderingState = RenderingStates.FINISHED;
          this.#useThumbnailCanvas.directDrawing = false;
        }
        this.cssTransform({
          redrawAnnotationLayer: true,
          redrawAnnotationEditorLayer: true,
          redrawXfaLayer: true,
          redrawTextLayer: !postponeDrawing,
          hideTextLayer: postponeDrawing
        });
        if (!postponeDrawing) {
          this.detailView?.update({
            underlyingViewUpdated: true
          });
          this.dispatchPageRendered(true, false);
        }
        return;
      }
    }
    this.cssTransform({});
    this.annotationEditorLayer?.update(this.viewport);
    this.reset({
      keepAnnotationLayer: true,
      keepAnnotationEditorLayer: true,
      keepXfaLayer: true,
      keepTextLayer: true,
      keepCanvasWrapper: true,
      preserveDetailViewState: true
    });
    this.detailView?.update({
      underlyingViewUpdated: true
    });
  }
  #computeScale() {
    const {
      width,
      height
    } = this.viewport;
    const outputScale = this.outputScale = new OutputScale();
    if (this.maxCanvasPixels === 0) {
      const invScale = 1 / this.scale;
      outputScale.sx *= invScale;
      outputScale.sy *= invScale;
      this.#needsRestrictedScaling = true;
    } else {
      this.#needsRestrictedScaling = outputScale.limitCanvas(width, height, this.maxCanvasPixels, this.maxCanvasDim, this.capCanvasAreaFactor);
      if (this.#needsRestrictedScaling && this.enableDetailCanvas) {
        const factor = this.enableOptimizedPartialRendering ? 4 : 2;
        outputScale.sx /= factor;
        outputScale.sy /= factor;
      }
    }
  }
  cancelRendering({
    keepAnnotationLayer = false,
    keepAnnotationEditorLayer = false,
    keepXfaLayer = false,
    keepTextLayer = false,
    cancelExtraDelay = 0
  } = {}) {
    super.cancelRendering({
      cancelExtraDelay
    });
    if (this.textLayer && (!keepTextLayer || !this.textLayer.div)) {
      this.textLayer.cancel();
      this.textLayer = null;
    }
    if (this.annotationLayer && (!keepAnnotationLayer || !this.annotationLayer.div)) {
      this.annotationLayer.cancel();
      this.annotationLayer = null;
      this._annotationCanvasMap = null;
    }
    if (this.structTreeLayer && !this.textLayer) {
      this.structTreeLayer = null;
    }
    if (this.annotationEditorLayer && (!keepAnnotationEditorLayer || !this.annotationEditorLayer.div || !this.textLayer)) {
      if (this.drawLayer) {
        this.drawLayer.cancel();
        this.drawLayer = null;
      }
      this.annotationEditorLayer.cancel();
      this.annotationEditorLayer = null;
    }
    if (this.drawLayer && !this.textLayer) {
      this.drawLayer.cancel();
      this.drawLayer = null;
    }
    if (this.xfaLayer && (!keepXfaLayer || !this.xfaLayer.div)) {
      this.xfaLayer.cancel();
      this.xfaLayer = null;
      this._textHighlighter?.disable();
    }
  }
  cssTransform({
    redrawAnnotationLayer = false,
    redrawAnnotationEditorLayer = false,
    redrawXfaLayer = false,
    redrawTextLayer = false,
    hideTextLayer = false
  }) {
    const {
      canvas
    } = this;
    if (!canvas) {
      return;
    }
    const originalViewport = this.#originalViewport;
    if (this.viewport !== originalViewport) {
      const relativeRotation = (360 + this.viewport.rotation - originalViewport.rotation) % 360;
      if (relativeRotation === 90 || relativeRotation === 270) {
        const {
          width,
          height
        } = this.viewport;
        const scaleX = height / width;
        const scaleY = width / height;
        canvas.style.transform = `rotate(${relativeRotation}deg) scale(${scaleX},${scaleY})`;
      } else {
        canvas.style.transform = relativeRotation === 0 ? "" : `rotate(${relativeRotation}deg)`;
      }
    }
    if (redrawAnnotationLayer && this.annotationLayer) {
      this.#renderAnnotationLayer();
    }
    if (redrawAnnotationEditorLayer && this.annotationEditorLayer) {
      if (this.drawLayer) {
        this.#renderDrawLayer();
      }
      this.#renderAnnotationEditorLayer();
    }
    if (redrawXfaLayer && this.xfaLayer) {
      this.#renderXfaLayer();
    }
    if (this.textLayer) {
      if (hideTextLayer) {
        this.textLayer.hide();
        this.structTreeLayer?.hide();
      } else if (redrawTextLayer) {
        this.#renderTextLayer();
      }
    }
  }
  get width() {
    return this.viewport.width;
  }
  get height() {
    return this.viewport.height;
  }
  getPagePoint(x, y) {
    return this.viewport.convertToPdfPoint(x, y);
  }
  _ensureCanvasWrapper() {
    let canvasWrapper = this.#canvasWrapper;
    if (!canvasWrapper) {
      canvasWrapper = this.#canvasWrapper = document.createElement("div");
      canvasWrapper.classList.add("canvasWrapper");
      this.#addLayer(canvasWrapper, "canvasWrapper");
    }
    return canvasWrapper;
  }
  _getRenderingContext(canvas, transform, recordOperations, recordImages) {
    return {
      canvas,
      transform,
      viewport: this.viewport,
      annotationMode: this.#annotationMode,
      optionalContentConfigPromise: this._optionalContentConfigPromise,
      annotationCanvasMap: this._annotationCanvasMap,
      pageColors: this.pageColors,
      isEditing: this.#isEditing,
      recordOperations,
      recordImages,
      partialFrames: true
    };
  }
  async draw() {
    if (this.renderingState !== RenderingStates.INITIAL) {
      console.error("Must be in new state before drawing");
      this.reset();
    }
    const {
      div,
      l10n,
      pdfPage,
      viewport
    } = this;
    if (!pdfPage) {
      this.renderingState = RenderingStates.FINISHED;
      throw new Error("pdfPage is not loaded");
    }
    this.renderingState = RenderingStates.RUNNING;
    const canvasWrapper = this._ensureCanvasWrapper();
    if (!this.textLayer && this.#textLayerMode !== TextLayerMode.DISABLE && !pdfPage.isPureXfa) {
      this._accessibilityManager ||= new TextAccessibilityManager();
      this.textLayer = new TextLayerBuilder({
        pdfPage,
        highlighter: this._textHighlighter,
        accessibilityManager: this._accessibilityManager,
        enablePermissions: this.#textLayerMode === TextLayerMode.ENABLE_PERMISSIONS,
        onAppend: textLayerDiv => {
          this.l10n.pause();
          this.#addLayer(textLayerDiv, "textLayer");
          this.l10n.resume();
        },
        abortSignal: this.#abortSignal
      });
      if (this.enableSelectionRendering) {
        this.textLayer.div.classList.add("selectionRendering");
      }
    }
    if (!this.annotationLayer && this.#annotationMode !== AnnotationMode.DISABLE) {
      const {
        annotationStorage,
        annotationEditorUIManager,
        downloadManager,
        enableComment,
        enableScripting,
        fieldObjectsPromise,
        hasJSActionsPromise,
        linkService
      } = this.#layerProperties;
      this._annotationCanvasMap ||= new Map();
      this.annotationLayer = new AnnotationLayerBuilder({
        pdfPage,
        annotationStorage,
        imageResourcesPath: this.imageResourcesPath,
        renderForms: this.#annotationMode === AnnotationMode.ENABLE_FORMS,
        linkService,
        downloadManager,
        enableComment,
        enableScripting,
        hasJSActionsPromise,
        fieldObjectsPromise,
        annotationCanvasMap: this._annotationCanvasMap,
        accessibilityManager: this._accessibilityManager,
        annotationEditorUIManager,
        commentManager: this.#commentManager,
        onAppend: annotationLayerDiv => {
          this.#addLayer(annotationLayerDiv, "annotationLayer");
        }
      });
    }
    const {
      width,
      height
    } = viewport;
    this.#originalViewport = viewport;
    const {
      canvas,
      prevCanvas
    } = this._createCanvas(newCanvas => {
      canvasWrapper.prepend(newCanvas);
    });
    canvas.setAttribute("role", "presentation");
    if (!this.outputScale) {
      this.#computeScale();
    }
    const {
      outputScale
    } = this;
    this.#hasRestrictedScaling = this.#needsRestrictedScaling;
    const sfx = approximateFraction(outputScale.sx);
    const sfy = approximateFraction(outputScale.sy);
    const canvasWidth = canvas.width = floorToDivide(calcRound(width * outputScale.sx), sfx[0]);
    const canvasHeight = canvas.height = floorToDivide(calcRound(height * outputScale.sy), sfy[0]);
    const pageWidth = floorToDivide(calcRound(width), sfx[1]);
    const pageHeight = floorToDivide(calcRound(height), sfy[1]);
    outputScale.sx = canvasWidth / pageWidth;
    outputScale.sy = canvasHeight / pageHeight;
    if (this.#scaleRoundX !== sfx[1]) {
      div.style.setProperty("--scale-round-x", `${sfx[1]}px`);
      this.#scaleRoundX = sfx[1];
    }
    if (this.#scaleRoundY !== sfy[1]) {
      div.style.setProperty("--scale-round-y", `${sfy[1]}px`);
      this.#scaleRoundY = sfy[1];
    }
    const recordBBoxes = this.enableOptimizedPartialRendering && this.#hasRestrictedScaling && !this.recordedBBoxes;
    const recordImages = this.imagesRightClickMinSize !== -1 && !this.imageCoordinates;
    const transform = outputScale.scaled ? [outputScale.sx, 0, 0, outputScale.sy, 0, 0] : null;
    const resultPromise = this._drawCanvas(this._getRenderingContext(canvas, transform, recordBBoxes, recordImages), () => {
      if (prevCanvas) {
        prevCanvas.remove();
        prevCanvas.width = prevCanvas.height = 0;
      }
      this._resetCanvas();
    }, renderTask => {
      this.#useThumbnailCanvas.regularAnnotations = !renderTask.separateAnnots;
      this.dispatchPageRendered(false, false);
    }).then(async () => {
      if (this.renderingState !== RenderingStates.FINISHED) {
        return;
      }
      this.structTreeLayer ||= new StructTreeLayerBuilder(pdfPage, viewport.rawDims);
      const textLayerPromise = this.textLayer ? this.#renderTextLayer() : null;
      if (this.annotationLayer) {
        await this.#renderAnnotationLayer(textLayerPromise);
      }
      this.drawLayer ||= new DrawLayerBuilder({
        pageIndex: this.id,
        textLayer: this.enableSelectionRendering ? this.textLayer?.div : null,
        filterFactory: this.pdfPage?.filterFactory,
        pageColors: this.pageColors
      });
      await this.#renderDrawLayer();
      this.drawLayer.setParent(canvasWrapper);
      const {
        annotationEditorUIManager
      } = this.#layerProperties;
      if (!annotationEditorUIManager) {
        return;
      }
      if (this.annotationLayer || this.#annotationMode === AnnotationMode.DISABLE) {
        this.annotationEditorLayer ||= new AnnotationEditorLayerBuilder({
          uiManager: annotationEditorUIManager,
          pageIndex: this.id - 1,
          l10n,
          structTreeLayer: this.structTreeLayer,
          accessibilityManager: this._accessibilityManager,
          annotationLayer: this.annotationLayer?.annotationLayer,
          textLayer: this.textLayer,
          drawLayer: this.drawLayer.getDrawLayer(),
          onAppend: annotationEditorLayerDiv => {
            this.#addLayer(annotationEditorLayerDiv, "annotationEditorLayer");
          }
        });
        this.#renderAnnotationEditorLayer();
      }
    });
    if (pdfPage.isPureXfa) {
      if (!this.xfaLayer) {
        const {
          annotationStorage,
          linkService
        } = this.#layerProperties;
        this.xfaLayer = new XfaLayerBuilder({
          pdfPage,
          annotationStorage,
          linkService
        });
      }
      this.#renderXfaLayer();
    }
    div.setAttribute("data-loaded", true);
    this.dispatchPageRender();
    return resultPromise;
  }
  setPageLabel(label) {
    this.pageLabel = typeof label === "string" ? label : null;
    this.div.setAttribute("data-l10n-args", JSON.stringify({
      page: this.pageLabel ?? this.id
    }));
    if (this.pageLabel !== null) {
      this.div.setAttribute("data-page-label", this.pageLabel);
    } else {
      this.div.removeAttribute("data-page-label");
    }
  }
  get thumbnailCanvas() {
    const {
      directDrawing,
      initialOptionalContent,
      regularAnnotations
    } = this.#useThumbnailCanvas;
    return directDrawing && initialOptionalContent && regularAnnotations ? this.canvas : null;
  }
}

;// ./web/pdf_viewer.js








const DEFAULT_CACHE_SIZE = 10;
const PagesCountLimit = {
  FORCE_SCROLL_MODE_PAGE: 10000,
  FORCE_LAZY_PAGE_INIT: 5000,
  PAUSE_EAGER_PAGE_INIT: 250
};
function isValidAnnotationEditorMode(mode) {
  return Object.values(AnnotationEditorType).includes(mode) && mode !== AnnotationEditorType.DISABLE;
}
class PDFPageViewBuffer {
  #buf = new Set();
  #size = 0;
  constructor(size) {
    this.#size = size;
  }
  push(view) {
    const buf = this.#buf;
    if (buf.has(view)) {
      buf.delete(view);
    }
    buf.add(view);
    if (buf.size > this.#size) {
      this.#destroyFirstView();
    }
  }
  resize(newSize, idsToKeep = null) {
    this.#size = newSize;
    const buf = this.#buf;
    if (idsToKeep) {
      const ii = buf.size;
      let i = 1;
      for (const view of buf) {
        if (idsToKeep.has(view.id)) {
          buf.delete(view);
          buf.add(view);
        }
        if (++i > ii) {
          break;
        }
      }
    }
    while (buf.size > this.#size) {
      this.#destroyFirstView();
    }
  }
  has(view) {
    return this.#buf.has(view);
  }
  [Symbol.iterator]() {
    return this.#buf.keys();
  }
  #destroyFirstView() {
    const firstView = this.#buf.keys().next().value;
    firstView?.destroy();
    this.#buf.delete(firstView);
  }
}
class PDFViewer {
  #buffer = null;
  #altTextManager = null;
  #annotationEditorHighlightColors = null;
  #annotationEditorMode = AnnotationEditorType.NONE;
  #annotationEditorUIManager = null;
  #annotationMode = AnnotationMode.ENABLE_FORMS;
  #commentManager = null;
  #containerTopLeft = null;
  #editorUndoBar = null;
  #enableHighlightFloatingButton = false;
  #enablePermissions = false;
  #enableUpdatedAddImage = false;
  #enableNewAltTextWhenAddingImage = false;
  #enableAutoLinking = true;
  #abortSignal = null;
  #eventAC = null;
  #minDurationToUpdateCanvas = 0;
  #mlManager = null;
  #panPosition = [NaN, NaN];
  #printingAllowed = true;
  #scrollTimeoutId = null;
  #staleLocation = false;
  #switchAnnotationEditorModeAC = null;
  #switchAnnotationEditorModeTimeoutId = null;
  #copyAllInProgress = false;
  #hiddenCopyElement = null;
  #previousContainerHeight = 0;
  #resizeObserver = new ResizeObserver(this.#resizeObserverCallback.bind(this));
  #scrollModePageState = null;
  #scaleTimeoutId = null;
  #signatureManager = null;
  #supportsPinchToZoom = true;
  #textLayerMode = TextLayerMode.ENABLE;
  #viewerAlert = null;
  #copiedPageViews = null;
  #savedPageViews = null;
  #deletedPageNumbers = null;
  constructor(options) {
    const viewerVersion = "6.5.438";
    if (version !== viewerVersion) {
      throw new Error(`The API version "${version}" does not match the Viewer version "${viewerVersion}".`);
    }
    this.container = options.container;
    this.viewer = options.viewer || options.container.firstElementChild;
    this.#viewerAlert = options.viewerAlert || null;
    if (this.container?.tagName !== "DIV" || this.viewer?.tagName !== "DIV") {
      throw new Error("Invalid `container` and/or `viewer` option.");
    }
    if (this.container.offsetParent && getComputedStyle(this.container).position !== "absolute") {
      throw new Error("The `container` must be absolutely positioned.");
    }
    this.#resizeObserver.observe(this.container);
    this.eventBus = options.eventBus;
    this.linkService = options.linkService || new SimpleLinkService();
    this.downloadManager = options.downloadManager || null;
    this.findController = options.findController || null;
    this.#altTextManager = options.altTextManager || null;
    this.#commentManager = options.commentManager || null;
    this.#signatureManager = options.signatureManager || null;
    this.#editorUndoBar = options.editorUndoBar || null;
    if (this.findController) {
      this.findController.onIsPageVisible = pageNumber => this._getVisiblePages().ids.has(pageNumber);
    }
    this._scriptingManager = options.scriptingManager || null;
    this.#textLayerMode = options.textLayerMode ?? TextLayerMode.ENABLE;
    this.#annotationMode = options.annotationMode ?? AnnotationMode.ENABLE_FORMS;
    this.#annotationEditorMode = options.annotationEditorMode ?? AnnotationEditorType.NONE;
    this.#annotationEditorHighlightColors = options.annotationEditorHighlightColors || null;
    this.#enableHighlightFloatingButton = options.enableHighlightFloatingButton === true;
    this.#enableUpdatedAddImage = options.enableUpdatedAddImage === true;
    this.#enableNewAltTextWhenAddingImage = options.enableNewAltTextWhenAddingImage === true;
    this.imageResourcesPath = options.imageResourcesPath || "";
    this.enablePrintAutoRotate = options.enablePrintAutoRotate || false;
    this.removePageBorders = options.removePageBorders || false;
    this.maxCanvasPixels = options.maxCanvasPixels;
    this.maxCanvasDim = options.maxCanvasDim;
    this.capCanvasAreaFactor = options.capCanvasAreaFactor;
    this.enableDetailCanvas = options.enableDetailCanvas ?? true;
    this.enableOptimizedPartialRendering = options.enableOptimizedPartialRendering ?? false;
    this.enableSelectionRendering = options.enableSelectionRendering !== false;
    this.imagesRightClickMinSize = options.imagesRightClickMinSize ?? -1;
    this.l10n = options.l10n;
    this.l10n ||= new genericl10n_GenericL10n();
    this.#enablePermissions = options.enablePermissions || false;
    this.pageColors = options.pageColors || null;
    this.#mlManager = options.mlManager || null;
    this.#supportsPinchToZoom = options.supportsPinchToZoom !== false;
    this.#enableAutoLinking = options.enableAutoLinking !== false;
    this.#minDurationToUpdateCanvas = options.minDurationToUpdateCanvas ?? 500;
    this.defaultRenderingQueue = !options.renderingQueue;
    if (this.defaultRenderingQueue) {
      this.renderingQueue = new PDFRenderingQueue();
      this.renderingQueue.setViewer(this);
    } else {
      this.renderingQueue = options.renderingQueue;
    }
    const {
      abortSignal
    } = options;
    this.#abortSignal = abortSignal || null;
    abortSignal?.addEventListener("abort", () => {
      this.#resizeObserver.disconnect();
      this.#resizeObserver = null;
    }, {
      once: true
    });
    this.scroll = watchScroll(this.container, this._scrollUpdate.bind(this), abortSignal);
    this.presentationModeState = PresentationModeState.UNKNOWN;
    this._resetView();
    if (this.removePageBorders) {
      this.viewer.classList.add("removePageBorders");
    }
    this.#updateContainerHeightCss();
    this.eventBus.on("thumbnailrendered", ({
      pageNumber,
      pdfPage
    }) => {
      const pageView = this._pages[pageNumber - 1];
      if (!this.#buffer.has(pageView)) {
        pdfPage?.cleanup();
      }
    }, internalOpt);
    if (!options.l10n) {
      this.l10n.translate(this.container);
    }
  }
  get printingAllowed() {
    return this.#printingAllowed;
  }
  get pagesCount() {
    return this._pages.length;
  }
  getPageView(index) {
    return this._pages[index];
  }
  getCachedPageViews() {
    return new Set(this.#buffer);
  }
  get pageViewsReady() {
    return this._pages.every(pageView => pageView?.pdfPage);
  }
  clearSelection() {
    const selection = document.getSelection();
    if (!selection || selection.isCollapsed) {
      return;
    }
    for (let i = 0, ii = selection.rangeCount; i < ii; i++) {
      if (selection.getRangeAt(i).intersectsNode(this.viewer)) {
        selection.removeAllRanges?.();
        selection.empty?.();
        return;
      }
    }
  }
  get renderForms() {
    return this.#annotationMode === AnnotationMode.ENABLE_FORMS;
  }
  get enableScripting() {
    return !!this._scriptingManager;
  }
  get currentPageNumber() {
    return this._currentPageNumber;
  }
  set currentPageNumber(val) {
    if (!Number.isInteger(val)) {
      throw new Error("Invalid page number.");
    }
    if (!this.pdfDocument) {
      return;
    }
    if (this._currentPageNumber !== val) {
      this.clearSelection();
    }
    if (!this._setCurrentPageNumber(val, true)) {
      console.error(`currentPageNumber: "${val}" is not a valid page.`);
    }
  }
  _setCurrentPageNumber(val, resetCurrentPageView = false) {
    if (this._currentPageNumber === val) {
      if (resetCurrentPageView) {
        this.#resetCurrentPageView();
      }
      return true;
    }
    if (!(0 < val && val <= this.pagesCount)) {
      return false;
    }
    const previous = this._currentPageNumber;
    this._currentPageNumber = val;
    this.eventBus.dispatch("pagechanging", {
      source: this,
      pageNumber: val,
      pageLabel: this._pageLabels?.[val - 1] ?? null,
      previous
    });
    if (resetCurrentPageView) {
      this.#resetCurrentPageView();
    }
    return true;
  }
  get currentPageLabel() {
    return this._pageLabels?.[this._currentPageNumber - 1] ?? null;
  }
  set currentPageLabel(val) {
    if (!this.pdfDocument) {
      return;
    }
    let page = val | 0;
    if (this._pageLabels) {
      const i = this._pageLabels.indexOf(val);
      if (i >= 0) {
        page = i + 1;
      }
    }
    if (this._currentPageNumber !== page) {
      this.clearSelection();
    }
    if (!this._setCurrentPageNumber(page, true)) {
      console.error(`currentPageLabel: "${val}" is not a valid page.`);
    }
  }
  get currentScale() {
    return this._currentScale !== (/* inlined export .UNKNOWN_SCALE */0) ? this._currentScale : (/* inlined export .DEFAULT_SCALE */1);
  }
  set currentScale(val) {
    if (isNaN(val)) {
      throw new Error("Invalid numeric scale.");
    }
    if (!this.pdfDocument) {
      return;
    }
    this.#setScale(val, {
      noScroll: false
    });
  }
  get currentScaleValue() {
    return this._currentScaleValue;
  }
  set currentScaleValue(val) {
    if (!this.pdfDocument) {
      return;
    }
    this.#setScale(val, {
      noScroll: false
    });
  }
  get pagesRotation() {
    return this._pagesRotation;
  }
  set pagesRotation(rotation) {
    if (!isValidRotation(rotation)) {
      throw new Error("Invalid pages rotation angle.");
    }
    if (!this.pdfDocument) {
      return;
    }
    rotation %= 360;
    if (rotation < 0) {
      rotation += 360;
    }
    if (this._pagesRotation === rotation) {
      return;
    }
    this.clearSelection();
    this._pagesRotation = rotation;
    const pageNumber = this._currentPageNumber;
    this.refresh(true, {
      rotation
    });
    if (this._currentScaleValue) {
      this.#setScale(this._currentScaleValue, {
        noScroll: true
      });
    }
    this.eventBus.dispatch("rotationchanging", {
      source: this,
      pagesRotation: rotation,
      pageNumber
    });
    if (this.defaultRenderingQueue) {
      this.update();
    }
  }
  get firstPagePromise() {
    return this.pdfDocument ? this._firstPageCapability.promise : null;
  }
  get onePageRendered() {
    return this.pdfDocument ? this._onePageRenderedCapability.promise : null;
  }
  get pagesPromise() {
    return this.pdfDocument ? this._pagesCapability.promise : null;
  }
  get _layerProperties() {
    const self = this;
    return shadow(this, "_layerProperties", {
      get annotationEditorUIManager() {
        return self.#annotationEditorUIManager;
      },
      get annotationStorage() {
        return self.pdfDocument?.annotationStorage;
      },
      get downloadManager() {
        return self.downloadManager;
      },
      get enableComment() {
        return !!self.#commentManager;
      },
      get enableScripting() {
        return !!self._scriptingManager;
      },
      get fieldObjectsPromise() {
        return self.pdfDocument?.getFieldObjects();
      },
      get findController() {
        return self.findController;
      },
      get hasJSActionsPromise() {
        return self.pdfDocument?.hasJSActions();
      },
      get linkService() {
        return self.linkService;
      }
    });
  }
  #setPrintingAllowed(isAllowed) {
    this.#printingAllowed = isAllowed;
    this.eventBus.dispatch("printingallowed", {
      source: this,
      isAllowed
    });
  }
  #initializePermissions(permissions) {
    const params = {
      annotationEditorMode: this.#annotationEditorMode,
      annotationMode: this.#annotationMode,
      textLayerMode: this.#textLayerMode
    };
    if (!permissions) {
      this.#setPrintingAllowed(true);
      return params;
    }
    this.#setPrintingAllowed(permissions.has(PermissionFlag.PRINT_HIGH_QUALITY) || permissions.has(PermissionFlag.PRINT));
    if (!permissions.has(PermissionFlag.COPY) && this.#textLayerMode === TextLayerMode.ENABLE) {
      params.textLayerMode = TextLayerMode.ENABLE_PERMISSIONS;
    }
    if (!permissions.has(PermissionFlag.MODIFY_CONTENTS)) {
      params.annotationEditorMode = AnnotationEditorType.DISABLE;
    }
    if (!permissions.has(PermissionFlag.MODIFY_ANNOTATIONS) && !permissions.has(PermissionFlag.FILL_INTERACTIVE_FORMS) && this.#annotationMode === AnnotationMode.ENABLE_FORMS) {
      params.annotationMode = AnnotationMode.ENABLE;
    }
    return params;
  }
  async #onePageRenderedOrForceFetch(signal) {
    if (document.visibilityState === "hidden" || !this.container.offsetParent || this._getVisiblePages().views.length === 0) {
      return;
    }
    const hiddenCapability = Promise.withResolvers(),
      ac = new AbortController();
    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden") {
        hiddenCapability.resolve();
      }
    }, {
      signal: AbortSignal.any([signal, ac.signal])
    });
    await Promise.race([this._onePageRenderedCapability.promise, hiddenCapability.promise]);
    ac.abort();
  }
  async getAllText(interruptSignal = null) {
    const texts = [];
    const buffer = [];
    for (let pageNum = 1, pagesCount = this.pdfDocument.numPages; pageNum <= pagesCount; ++pageNum) {
      if (interruptSignal?.aborted) {
        return null;
      }
      buffer.length = 0;
      const page = await this.pdfDocument.getPage(pageNum);
      const {
        items
      } = await page.getTextContent();
      for (const item of items) {
        if (item.str) {
          buffer.push(item.str);
        }
        if (item.hasEOL) {
          buffer.push("\n");
        }
      }
      texts.push(removeNullCharacters(buffer.join("")));
    }
    return texts.join("\n");
  }
  #copyCallback(textLayerMode, event) {
    const selection = document.getSelection();
    const {
      focusNode,
      anchorNode
    } = selection;
    if (anchorNode && focusNode && selection.containsNode(this.#hiddenCopyElement)) {
      if (this.#copyAllInProgress || textLayerMode === TextLayerMode.ENABLE_PERMISSIONS) {
        stopEvent(event);
        return;
      }
      this.#copyAllInProgress = true;
      const {
        classList
      } = this.viewer;
      classList.add("copyAll");
      const keydownAC = new AbortController(),
        interruptAC = new AbortController();
      window.addEventListener("keydown", ev => {
        if (ev.key === "Escape") {
          interruptAC.abort();
        }
      }, {
        signal: keydownAC.signal
      });
      this.getAllText(interruptAC.signal).then(async text => {
        if (text !== null) {
          await navigator.clipboard.writeText(text);
        }
      }).catch(reason => {
        console.warn(`Something goes wrong when extracting the text: ${reason.message}`);
      }).finally(() => {
        this.#copyAllInProgress = false;
        keydownAC.abort();
        classList.remove("copyAll");
      });
      stopEvent(event);
    }
  }
  setDocument(pdfDocument) {
    if (this.pdfDocument) {
      this.eventBus.dispatch("pagesdestroy", {
        source: this
      });
      this._cancelRendering();
      this._resetView();
      this.findController?.setDocument(null);
      this._scriptingManager?.setDocument(null);
      this.#annotationEditorUIManager?.destroy();
      this.#annotationEditorUIManager = null;
      if (this.#annotationEditorMode !== AnnotationEditorType.DISABLE) {
        this.#annotationEditorMode = AnnotationEditorType.NONE;
      }
      this.#printingAllowed = true;
    }
    this.pdfDocument = pdfDocument;
    if (!pdfDocument) {
      return;
    }
    const pagesCount = pdfDocument.numPages;
    const firstPagePromise = pdfDocument.getPage(1);
    const optionalContentConfigPromise = pdfDocument.getOptionalContentConfig({
      intent: "display"
    });
    const permissionsPromise = this.#enablePermissions ? pdfDocument.getPermissions().catch(reason => {
      console.error("getPermissions", reason);
    }) : Promise.resolve();
    const {
      eventBus,
      pageColors,
      viewer
    } = this;
    this.#eventAC = new AbortController();
    const {
      signal
    } = this.#eventAC;
    const evtOpts = {
      signal,
      ...internalOpt
    };
    if (pagesCount > PagesCountLimit.FORCE_SCROLL_MODE_PAGE) {
      console.warn("Forcing PAGE-scrolling for performance reasons, given the length of the document.");
      const mode = this._scrollMode = ScrollMode.PAGE;
      eventBus.dispatch("scrollmodechanged", {
        source: this,
        mode
      });
    }
    this._pagesCapability.promise.then(() => {
      eventBus.dispatch("pagesloaded", {
        source: this,
        pagesCount
      });
    }, () => {});
    const onBeforeDraw = evt => {
      const pageView = this._pages[evt.pageNumber - 1];
      if (!pageView) {
        return;
      }
      this.#buffer.push(pageView);
    };
    eventBus.on("pagerender", onBeforeDraw, evtOpts);
    const onAfterDraw = evt => {
      if (evt.cssTransform || evt.isDetailView) {
        return;
      }
      this._onePageRenderedCapability.resolve({
        timestamp: evt.timestamp
      });
      eventBus.off("pagerendered", onAfterDraw);
    };
    eventBus.on("pagerendered", onAfterDraw, evtOpts);
    Promise.all([firstPagePromise, permissionsPromise]).then(([firstPdfPage, permissions]) => {
      if (pdfDocument !== this.pdfDocument) {
        return;
      }
      this._firstPageCapability.resolve(firstPdfPage);
      this._optionalContentConfigPromise = optionalContentConfigPromise;
      const {
        annotationEditorMode,
        annotationMode,
        textLayerMode
      } = this.#initializePermissions(permissions);
      if (textLayerMode !== TextLayerMode.DISABLE) {
        const element = this.#hiddenCopyElement = document.createElement("div");
        element.id = "hiddenCopyElement";
        element.style.cssText = "position:absolute;top:0;left:0;width:0;height:0;display:none";
        viewer.before(element);
      }
      if (annotationEditorMode !== AnnotationEditorType.DISABLE) {
        const mode = annotationEditorMode;
        if (pdfDocument.isPureXfa) {
          console.warn("Warning: XFA-editing is not implemented.");
        } else if (isValidAnnotationEditorMode(mode)) {
          this.#annotationEditorUIManager = new AnnotationEditorUIManager(this.container, viewer, this.#viewerAlert, this.#altTextManager, this.#commentManager, this.#signatureManager, eventBus, pdfDocument, pageColors, this.#annotationEditorHighlightColors, this.#enableHighlightFloatingButton, this.#enableUpdatedAddImage, this.#enableNewAltTextWhenAddingImage, this.#mlManager, this.#editorUndoBar, this.#supportsPinchToZoom, false);
          eventBus.dispatch("annotationeditoruimanager", {
            source: this,
            uiManager: this.#annotationEditorUIManager
          });
          if (mode !== AnnotationEditorType.NONE) {
            this.#preloadEditingData(mode);
            this.#annotationEditorUIManager.updateMode(mode);
          }
        } else {
          console.error(`Invalid AnnotationEditor mode: ${mode}`);
        }
      }
      const viewerElement = this._scrollMode === ScrollMode.PAGE ? null : viewer;
      const scale = this.currentScale;
      const viewport = firstPdfPage.getViewport({
        scale: scale * PixelsPerInch.PDF_TO_CSS_UNITS
      });
      viewer.style.setProperty("--scale-factor", viewport.scale);
      if (pageColors?.background) {
        viewer.style.setProperty("--page-bg-color", pageColors.background);
      }
      if (pageColors?.foreground === "CanvasText" || pageColors?.background === "Canvas") {
        viewer.style.setProperty("--hcm-highlight-filter", pdfDocument.filterFactory.addHighlightHCMFilter("highlight", "CanvasText", "Canvas", "HighlightText", "Highlight"));
        viewer.style.setProperty("--hcm-highlight-selected-filter", pdfDocument.filterFactory.addHighlightHCMFilter("highlight_selected", "CanvasText", "Canvas", "HighlightText", "ButtonText"));
      }
      for (let pageNum = 1; pageNum <= pagesCount; ++pageNum) {
        const pageView = new PDFPageView({
          container: viewerElement,
          eventBus,
          id: pageNum,
          scale,
          defaultViewport: viewport.clone(),
          optionalContentConfigPromise,
          renderingQueue: this.renderingQueue,
          textLayerMode,
          annotationMode,
          imageResourcesPath: this.imageResourcesPath,
          maxCanvasPixels: this.maxCanvasPixels,
          maxCanvasDim: this.maxCanvasDim,
          capCanvasAreaFactor: this.capCanvasAreaFactor,
          enableDetailCanvas: this.enableDetailCanvas,
          enableOptimizedPartialRendering: this.enableOptimizedPartialRendering,
          enableSelectionRendering: this.enableSelectionRendering,
          imagesRightClickMinSize: this.imagesRightClickMinSize,
          pageColors,
          l10n: this.l10n,
          layerProperties: this._layerProperties,
          enableAutoLinking: this.#enableAutoLinking,
          minDurationToUpdateCanvas: this.#minDurationToUpdateCanvas,
          commentManager: this.#commentManager,
          abortSignal: this.#abortSignal
        });
        this._pages.push(pageView);
      }
      this._pages[0]?.setPdfPage(firstPdfPage);
      if (this._scrollMode === ScrollMode.PAGE) {
        this.#ensurePageViewVisible();
      } else if (this._spreadMode !== SpreadMode.NONE) {
        this._updateSpreadMode();
      }
      eventBus.on("annotationeditorlayerrendered", evt => {
        if (this.#annotationEditorUIManager) {
          eventBus.dispatch("annotationeditormodechanged", {
            source: this,
            mode: this.#annotationEditorMode
          });
        }
      }, {
        once: true,
        signal,
        ...internalOpt
      });
      this.#onePageRenderedOrForceFetch(signal).then(async () => {
        if (pdfDocument !== this.pdfDocument) {
          return;
        }
        this.findController?.setDocument(pdfDocument);
        this._scriptingManager?.setDocument(pdfDocument);
        if (this.#hiddenCopyElement) {
          document.addEventListener("copy", this.#copyCallback.bind(this, textLayerMode), {
            signal
          });
        }
        if (pdfDocument.loadingParams.disableAutoFetch || pagesCount > PagesCountLimit.FORCE_LAZY_PAGE_INIT) {
          this._pagesCapability.resolve();
          return;
        }
        let getPagesLeft = pagesCount - 1;
        if (getPagesLeft <= 0) {
          this._pagesCapability.resolve();
          return;
        }
        for (let pageNum = 2; pageNum <= pagesCount; ++pageNum) {
          const promise = pdfDocument.getPage(pageNum).then(pdfPage => {
            const pageView = this._pages[pageNum - 1];
            if (!pageView.pdfPage) {
              pageView.setPdfPage(pdfPage);
            }
            if (--getPagesLeft === 0) {
              this._pagesCapability.resolve();
            }
          }, reason => {
            console.error(`Unable to get page ${pageNum} to initialize viewer`, reason);
            if (--getPagesLeft === 0) {
              this._pagesCapability.resolve();
            }
          });
          if (pageNum % PagesCountLimit.PAUSE_EAGER_PAGE_INIT === 0) {
            await promise;
          }
        }
      });
      eventBus.dispatch("pagesinit", {
        source: this
      });
      pdfDocument.getMetadata().then(({
        info
      }) => {
        if (pdfDocument !== this.pdfDocument) {
          return;
        }
        if (info.Language) {
          viewer.lang = info.Language;
        }
      });
      if (this.defaultRenderingQueue) {
        this.update();
      }
    }).catch(reason => {
      console.error("Unable to initialize viewer", reason);
      this._pagesCapability.reject(reason);
    });
  }
  onPagesEdited({
    pagesMapper,
    type,
    hasBeenCut,
    pageNumbers
  }) {
    if (type === "copy") {
      this.#copiedPageViews = new Map();
      for (const pageNum of pageNumbers) {
        this.#copiedPageViews.set(pageNum, this._pages[pageNum - 1]);
      }
      return;
    }
    if (type === "cancelCopy") {
      this.#copiedPageViews = null;
      return;
    }
    const isCut = type === "cut";
    if (isCut || type === "delete") {
      this.#savedPageViews = this._pages;
      this.#deletedPageNumbers = pageNumbers;
    }
    if (type === "cancelDelete") {
      this.#deletedPageNumbers = null;
      if (!this.#savedPageViews) {
        return;
      }
      const viewerElement = this._scrollMode === ScrollMode.PAGE ? null : this.viewer;
      if (viewerElement) {
        this.#annotationEditorUIManager?.startUpdatePages();
        const fragment = document.createDocumentFragment();
        for (let i = 0, ii = this.#savedPageViews.length; i < ii; i++) {
          const page = this.#savedPageViews[i];
          page.updatePageNumber(i + 1);
          fragment.append(page.div);
        }
        viewerElement.replaceChildren(fragment);
        this.#annotationEditorUIManager?.endUpdatePages();
      }
      this._pages = this.#savedPageViews;
      this.#savedPageViews = null;
      return;
    }
    if (type === "cleanSavedData") {
      if (this.#deletedPageNumbers) {
        if (this.#savedPageViews) {
          for (const pageNum of this.#deletedPageNumbers) {
            this.#savedPageViews[pageNum - 1].deleteMe();
          }
          this.#savedPageViews = null;
        }
        this.#deletedPageNumbers = null;
      }
      return;
    }
    this._currentPageNumber = 0;
    const prevPages = this._pages;
    const newPages = this._pages = [];
    this.#annotationEditorUIManager?.startUpdatePages();
    for (let i = 1, ii = pagesMapper.pagesNumber; i <= ii; i++) {
      const prevPageNumber = pagesMapper.getPrevPageNumber(i);
      if (prevPageNumber < 0) {
        let page = this.#copiedPageViews.get(-prevPageNumber);
        if (hasBeenCut) {
          page.updatePageNumber(i);
        } else {
          this.#annotationEditorUIManager?.clonePage(-prevPageNumber - 1, i - 1);
          page = page.clone(i);
        }
        newPages.push(page);
        continue;
      }
      const page = prevPages[prevPageNumber - 1];
      newPages.push(page);
      page.updatePageNumber(i);
    }
    this.#annotationEditorUIManager?.endUpdatePages();
    if (type === "paste") {
      this.#copiedPageViews = null;
    }
    const viewerElement = this._scrollMode === ScrollMode.PAGE ? null : this.viewer;
    if (viewerElement) {
      const fragment = document.createDocumentFragment();
      for (const {
        div
      } of newPages) {
        fragment.append(div);
      }
      viewerElement.replaceChildren(fragment);
    }
    setTimeout(() => {
      this.forceRendering();
    });
  }
  setPageLabels(labels) {
    if (!this.pdfDocument) {
      return;
    }
    if (!labels) {
      this._pageLabels = null;
    } else if (!(Array.isArray(labels) && this.pdfDocument.numPages === labels.length)) {
      this._pageLabels = null;
      console.error(`setPageLabels: Invalid page labels.`);
    } else {
      this._pageLabels = labels;
    }
    for (let i = 0, ii = this._pages.length; i < ii; i++) {
      this._pages[i].setPageLabel(this._pageLabels?.[i] ?? null);
    }
  }
  _resetView() {
    this._pages = [];
    this._currentPageNumber = 1;
    this._currentScale = (/* inlined export .UNKNOWN_SCALE */0);
    this._currentScaleValue = null;
    this._pageLabels = null;
    this.#buffer = new PDFPageViewBuffer(DEFAULT_CACHE_SIZE);
    this._location = null;
    this._pagesRotation = 0;
    this._optionalContentConfigPromise = null;
    this._firstPageCapability = Promise.withResolvers();
    this._onePageRenderedCapability = Promise.withResolvers();
    this._pagesCapability = Promise.withResolvers();
    this._scrollMode = ScrollMode.VERTICAL;
    this._previousScrollMode = ScrollMode.UNKNOWN;
    this._spreadMode = SpreadMode.NONE;
    this.#scrollModePageState = {
      previousPageNumber: 1,
      scrollDown: true,
      pages: []
    };
    this.#eventAC?.abort();
    this.#eventAC = null;
    this.viewer.textContent = "";
    this._updateScrollMode();
    this.viewer.removeAttribute("lang");
    this.#hiddenCopyElement?.remove();
    this.#hiddenCopyElement = null;
    this.#cleanupTimeouts();
    this.#cleanupSwitchAnnotationEditorMode();
  }
  #ensurePageViewVisible() {
    if (this._scrollMode !== ScrollMode.PAGE) {
      throw new Error("#ensurePageViewVisible: Invalid scrollMode value.");
    }
    const pageNumber = this._currentPageNumber,
      state = this.#scrollModePageState,
      viewer = this.viewer;
    this.l10n.pause();
    viewer.textContent = "";
    state.pages.length = 0;
    if (this._spreadMode === SpreadMode.NONE && !this.isInPresentationMode) {
      const pageView = this._pages[pageNumber - 1];
      viewer.append(pageView.div);
      state.pages.push(pageView);
    } else {
      const pageIndexSet = new Set(),
        parity = this._spreadMode - 1;
      if (parity === -1) {
        pageIndexSet.add(pageNumber - 1);
      } else if (pageNumber % 2 !== parity) {
        pageIndexSet.add(pageNumber - 1);
        pageIndexSet.add(pageNumber);
      } else {
        pageIndexSet.add(pageNumber - 2);
        pageIndexSet.add(pageNumber - 1);
      }
      const spread = document.createElement("div");
      spread.className = "spread";
      if (this.isInPresentationMode) {
        const dummyPage = document.createElement("div");
        dummyPage.className = "dummyPage";
        spread.append(dummyPage);
      }
      for (const i of pageIndexSet) {
        const pageView = this._pages[i];
        if (!pageView) {
          continue;
        }
        spread.append(pageView.div);
        state.pages.push(pageView);
      }
      viewer.append(spread);
    }
    this.l10n.resume();
    state.scrollDown = pageNumber >= state.previousPageNumber;
    state.previousPageNumber = pageNumber;
  }
  _scrollUpdate() {
    if (this.pagesCount === 0) {
      return;
    }
    if (this.#scrollTimeoutId) {
      clearTimeout(this.#scrollTimeoutId);
    }
    this.#scrollTimeoutId = setTimeout(() => {
      this.#scrollTimeoutId = null;
      this.update();
    }, 100);
    this.update();
  }
  #scrollIntoView(pageView, pageSpot = null) {
    const {
      div,
      id
    } = pageView;
    if (this._currentPageNumber !== id) {
      this._setCurrentPageNumber(id);
    }
    if (this._scrollMode === ScrollMode.PAGE) {
      this.#ensurePageViewVisible();
      this.update();
    }
    if (!pageSpot && !this.isInPresentationMode) {
      const left = div.offsetLeft + div.clientLeft,
        right = left + div.clientWidth;
      const {
        scrollLeft,
        clientWidth
      } = this.container;
      if (this._scrollMode === ScrollMode.HORIZONTAL || left < scrollLeft || right > scrollLeft + clientWidth) {
        pageSpot = {
          left: 0,
          top: 0
        };
      }
    }
    scrollIntoView(div, pageSpot);
    if (!this._currentScaleValue && this._location) {
      this._location = null;
    }
  }
  #isSameScale(newScale) {
    return newScale === this._currentScale || Math.abs(newScale - this._currentScale) < 1e-15;
  }
  panBy(dx, dy) {
    const {
      container
    } = this;
    const position = this.#panPosition;
    const {
      scrollLeft,
      scrollTop
    } = container;
    const left = (Math.abs(scrollLeft - position[0]) < 1 ? position[0] : scrollLeft) - dx;
    const top = (Math.abs(scrollTop - position[1]) < 1 ? position[1] : scrollTop) - dy;
    position[0] = left;
    position[1] = top;
    container.scrollLeft = left;
    container.scrollTop = top;
    this.#staleLocation = true;
  }
  #refreshLocation() {
    if (!this.#staleLocation) {
      return;
    }
    const {
      first
    } = this._getVisiblePages();
    if (first) {
      this._updateLocation(first);
    }
  }
  #setScaleUpdatePages(newScale, newValue, {
    noScroll = false,
    preset = false,
    drawingDelay = -1,
    origin = null,
    pan = null
  }) {
    this._currentScaleValue = newValue.toString();
    if (this.#isSameScale(newScale)) {
      if (pan && !noScroll) {
        this.panBy(pan[0], pan[1]);
      }
      if (preset) {
        this.eventBus.dispatch("scalechanging", {
          source: this,
          scale: newScale,
          presetValue: newValue
        });
      }
      return;
    }
    this.clearSelection();
    this.viewer.style.setProperty("--scale-factor", newScale * PixelsPerInch.PDF_TO_CSS_UNITS);
    const postponeDrawing = drawingDelay >= 0 && drawingDelay < 1000;
    this.refresh(true, {
      scale: newScale,
      drawingDelay: postponeDrawing ? drawingDelay : -1
    });
    if (postponeDrawing) {
      this.#scaleTimeoutId = setTimeout(() => {
        this.#scaleTimeoutId = null;
        this.refresh();
      }, drawingDelay);
    }
    const previousScale = this._currentScale;
    this._currentScale = newScale;
    if (!noScroll) {
      this.#refreshLocation();
      let page = this._currentPageNumber,
        dest;
      if (this._location && !(this.isInPresentationMode || this.isChangingPresentationMode)) {
        page = this._location.pageNumber;
        dest = [null, {
          name: "XYZ"
        }, this._location.left, this._location.top, null];
      }
      this.scrollPageIntoView({
        pageNumber: page,
        destArray: dest,
        allowNegativeOffset: true
      });
      let dx = pan?.[0] ?? 0,
        dy = pan?.[1] ?? 0;
      if (Array.isArray(origin)) {
        const scaleDiff = newScale / previousScale - 1;
        const [top, left] = this.containerTopLeft;
        dx -= (origin[0] - left) * scaleDiff;
        dy -= (origin[1] - top) * scaleDiff;
      }
      if (dx || dy) {
        this.panBy(dx, dy);
      }
    }
    this.eventBus.dispatch("scalechanging", {
      source: this,
      scale: newScale,
      presetValue: preset ? newValue : undefined
    });
    if (this.defaultRenderingQueue) {
      this.update();
    }
  }
  get #pageWidthScaleFactor() {
    return this._spreadMode !== SpreadMode.NONE && this._scrollMode !== ScrollMode.HORIZONTAL ? 2 : 1;
  }
  #setScale(value, options) {
    let scale = parseFloat(value);
    if (scale > 0) {
      options.preset = false;
      this.#setScaleUpdatePages(scale, value, options);
    } else {
      const currentPage = this._pages[this._currentPageNumber - 1];
      if (!currentPage) {
        return;
      }
      let hPadding = (/* inlined export .SCROLLBAR_PADDING */40),
        vPadding = (/* inlined export .VERTICAL_PADDING */5);
      if (this.isInPresentationMode) {
        hPadding = vPadding = 4;
        if (this._spreadMode !== SpreadMode.NONE) {
          hPadding *= 2;
        }
      } else if (this.removePageBorders) {
        hPadding = vPadding = 0;
      } else if (this._scrollMode === ScrollMode.HORIZONTAL) {
        [hPadding, vPadding] = [vPadding, hPadding];
      }
      const pageWidthScale = (this.container.clientWidth - hPadding) / currentPage.width * currentPage.scale / this.#pageWidthScaleFactor;
      const pageHeightScale = (this.container.clientHeight - vPadding) / currentPage.height * currentPage.scale;
      switch (value) {
        case "page-actual":
          scale = 1;
          break;
        case "page-width":
          scale = pageWidthScale;
          break;
        case "page-height":
          scale = pageHeightScale;
          break;
        case "page-fit":
          scale = Math.min(pageWidthScale, pageHeightScale);
          break;
        case "auto":
          const horizontalScale = isPortraitOrientation(currentPage) ? pageWidthScale : Math.min(pageHeightScale, pageWidthScale);
          scale = Math.min((/* inlined export .MAX_AUTO_SCALE */1.25), horizontalScale);
          break;
        default:
          console.error(`#setScale: "${value}" is an unknown zoom value.`);
          return;
      }
      options.preset = true;
      this.#setScaleUpdatePages(scale, value, options);
    }
  }
  #resetCurrentPageView() {
    const pageView = this._pages[this._currentPageNumber - 1];
    if (this.isInPresentationMode) {
      this.#setScale(this._currentScaleValue, {
        noScroll: true
      });
    }
    this.#scrollIntoView(pageView);
  }
  pageLabelToPageNumber(label) {
    if (!this._pageLabels) {
      return null;
    }
    const i = this._pageLabels.indexOf(label);
    return i < 0 ? null : i + 1;
  }
  scrollPageIntoView({
    pageNumber,
    destArray = null,
    allowNegativeOffset = false,
    ignoreDestinationZoom = false,
    center = null
  }) {
    if (!this.pdfDocument) {
      return;
    }
    const pageView = Number.isInteger(pageNumber) && this._pages[pageNumber - 1];
    if (!pageView) {
      console.error(`scrollPageIntoView: "${pageNumber}" is not a valid pageNumber parameter.`);
      return;
    }
    if (this.isInPresentationMode || !destArray) {
      this._setCurrentPageNumber(pageNumber, true);
      return;
    }
    let x = 0,
      y = 0;
    let width = 0,
      height = 0,
      widthScale,
      heightScale;
    const changeOrientation = pageView.rotation % 180 !== 0;
    const pageWidth = (changeOrientation ? pageView.height : pageView.width) / pageView.scale / PixelsPerInch.PDF_TO_CSS_UNITS;
    const pageHeight = (changeOrientation ? pageView.width : pageView.height) / pageView.scale / PixelsPerInch.PDF_TO_CSS_UNITS;
    let scale = 0;
    switch (destArray[1].name) {
      case "XYZ":
        x = destArray[2];
        y = destArray[3];
        scale = destArray[4];
        x = x !== null ? x : 0;
        y = y !== null ? y : pageHeight;
        break;
      case "Fit":
      case "FitB":
        scale = "page-fit";
        break;
      case "FitH":
      case "FitBH":
        y = destArray[2];
        scale = "page-width";
        if (y === null && this._location) {
          x = this._location.left;
          y = this._location.top;
        } else if (typeof y !== "number" || y < 0) {
          y = pageHeight;
        }
        break;
      case "FitV":
      case "FitBV":
        x = destArray[2];
        width = pageWidth;
        height = pageHeight;
        scale = "page-height";
        break;
      case "FitR":
        x = destArray[2];
        y = destArray[3];
        width = destArray[4] - x;
        height = destArray[5] - y;
        let hPadding = (/* inlined export .SCROLLBAR_PADDING */40),
          vPadding = (/* inlined export .VERTICAL_PADDING */5);
        if (this.removePageBorders) {
          hPadding = vPadding = 0;
        }
        widthScale = (this.container.clientWidth - hPadding) / width / PixelsPerInch.PDF_TO_CSS_UNITS;
        heightScale = (this.container.clientHeight - vPadding) / height / PixelsPerInch.PDF_TO_CSS_UNITS;
        scale = Math.min(Math.abs(widthScale), Math.abs(heightScale));
        break;
      default:
        console.error(`scrollPageIntoView: "${destArray[1].name}" is not a valid destination type.`);
        return;
    }
    if (!ignoreDestinationZoom) {
      if (scale && scale !== this._currentScale) {
        this.currentScaleValue = scale;
      } else if (this._currentScale === (/* inlined export .UNKNOWN_SCALE */0)) {
        this.currentScaleValue = (/* inlined export .DEFAULT_SCALE_VALUE */"auto");
      }
    }
    if (scale === "page-fit" && !destArray[4]) {
      this.#scrollIntoView(pageView);
      return;
    }
    const boundingRect = [pageView.viewport.convertToViewportPoint(x, y), pageView.viewport.convertToViewportPoint(x + width, y + height)];
    let left = Math.min(boundingRect[0][0], boundingRect[1][0]);
    let top = Math.min(boundingRect[0][1], boundingRect[1][1]);
    if (center) {
      if (center === "both" || center === "vertical") {
        top -= (this.container.clientHeight - Math.abs(boundingRect[1][1] - boundingRect[0][1])) / 2;
      }
      if (center === "both" || center === "horizontal") {
        left -= (this.container.clientWidth - Math.abs(boundingRect[1][0] - boundingRect[0][0])) / 2;
      }
    } else if (!allowNegativeOffset) {
      left = Math.max(left, 0);
      top = Math.max(top, 0);
    }
    this.#scrollIntoView(pageView, {
      left,
      top
    });
  }
  _updateLocation(firstPage) {
    this.#staleLocation = false;
    const currentScale = this._currentScale;
    const currentScaleValue = this._currentScaleValue;
    const normalizedScaleValue = parseFloat(currentScaleValue) === currentScale ? Math.round(currentScale * 10000) / 100 : currentScaleValue;
    const pageNumber = firstPage.id;
    const currentPageView = this._pages[pageNumber - 1];
    const container = this.container;
    const topLeft = currentPageView.getPagePoint(container.scrollLeft - firstPage.x, container.scrollTop - firstPage.y);
    const [left, top] = topLeft;
    let pdfOpenParams = `#page=${pageNumber}`;
    if (!this.isInPresentationMode) {
      pdfOpenParams += `&zoom=${normalizedScaleValue},` + `${Math.round(left)},${Math.round(top)}`;
    }
    this._location = {
      pageNumber,
      scale: normalizedScaleValue,
      top,
      left,
      rotation: this._pagesRotation,
      pdfOpenParams
    };
  }
  update() {
    const visible = this._getVisiblePages();
    const visiblePages = visible.views,
      numVisiblePages = visiblePages.length;
    if (numVisiblePages === 0) {
      return;
    }
    const newCacheSize = Math.max(DEFAULT_CACHE_SIZE, 2 * numVisiblePages + 1);
    this.#buffer.resize(newCacheSize, visible.ids);
    for (const {
      view,
      visibleArea
    } of visiblePages) {
      view.updateVisibleArea(visibleArea);
    }
    for (const view of this.#buffer) {
      if (!visible.ids.has(view.id)) {
        view.updateVisibleArea(null);
      }
    }
    this.renderingQueue.renderHighestPriority(visible);
    const isSimpleLayout = this._spreadMode === SpreadMode.NONE && (this._scrollMode === ScrollMode.PAGE || this._scrollMode === ScrollMode.VERTICAL);
    const currentPageNumber = this._currentPageNumber;
    let stillFullyVisible = false;
    for (const page of visiblePages) {
      if (page.percent < 100) {
        break;
      }
      if (page.id === currentPageNumber && isSimpleLayout) {
        stillFullyVisible = true;
        break;
      }
    }
    this._setCurrentPageNumber(stillFullyVisible ? this._currentPageNumber : visiblePages[0].id);
    this._updateLocation(visible.first);
    this.eventBus.dispatch("updateviewarea", {
      source: this,
      location: this._location
    });
  }
  #switchToEditAnnotationMode() {
    const visible = this._getVisiblePages();
    const pagesToRefresh = [];
    const {
      ids,
      views
    } = visible;
    for (const page of views) {
      const {
        view
      } = page;
      if (!view.hasEditableAnnotations()) {
        ids.delete(view.id);
        continue;
      }
      pagesToRefresh.push(page);
    }
    if (pagesToRefresh.length === 0) {
      return null;
    }
    this.renderingQueue.renderHighestPriority({
      first: pagesToRefresh[0],
      last: pagesToRefresh.at(-1),
      views: pagesToRefresh,
      ids
    });
    return ids;
  }
  containsElement(element) {
    return this.container.contains(element);
  }
  focus() {
    this.container.focus();
  }
  get _isContainerRtl() {
    return getComputedStyle(this.container).direction === "rtl";
  }
  get isInPresentationMode() {
    return this.presentationModeState === PresentationModeState.FULLSCREEN;
  }
  get isChangingPresentationMode() {
    return this.presentationModeState === PresentationModeState.CHANGING;
  }
  get isHorizontalScrollbarEnabled() {
    return !this.isInPresentationMode && this.container.scrollWidth > this.container.clientWidth;
  }
  get isVerticalScrollbarEnabled() {
    return !this.isInPresentationMode && this.container.scrollHeight > this.container.clientHeight;
  }
  _getVisiblePages() {
    const views = this._scrollMode === ScrollMode.PAGE ? this.#scrollModePageState.pages : this._pages,
      horizontal = this._scrollMode === ScrollMode.HORIZONTAL,
      rtl = horizontal && this._isContainerRtl;
    return getVisibleElements({
      scrollEl: this.container,
      views,
      sortByVisibility: true,
      horizontal,
      rtl
    });
  }
  cleanup() {
    for (const pageView of this._pages) {
      if (pageView.renderingState !== RenderingStates.FINISHED) {
        pageView.reset();
      }
    }
  }
  _cancelRendering() {
    for (const pageView of this._pages) {
      pageView.cancelRendering();
    }
  }
  async #ensurePdfPageLoaded(pageView) {
    if (pageView.pdfPage) {
      return pageView.pdfPage;
    }
    try {
      const pdfPage = await this.pdfDocument.getPage(pageView.id);
      if (!pageView.pdfPage) {
        pageView.setPdfPage(pdfPage);
      }
      return pdfPage;
    } catch (reason) {
      console.error("Unable to get page for page view", reason);
      return null;
    }
  }
  #getScrollAhead(visible) {
    if (visible.first?.id === 1) {
      return true;
    } else if (visible.last?.id === this.pagesCount) {
      return false;
    }
    switch (this._scrollMode) {
      case ScrollMode.PAGE:
        return this.#scrollModePageState.scrollDown;
      case ScrollMode.HORIZONTAL:
        return this.scroll.right;
    }
    return this.scroll.down;
  }
  forceRendering(currentlyVisiblePages) {
    const visiblePages = currentlyVisiblePages || this._getVisiblePages();
    const scrollAhead = this.#getScrollAhead(visiblePages);
    const preRenderExtra = this._spreadMode !== SpreadMode.NONE && this._scrollMode !== ScrollMode.HORIZONTAL;
    const ignoreDetailViews = this.#scaleTimeoutId !== null || this.#scrollTimeoutId !== null && visiblePages.views.some(page => page.detailView?.renderingCancelled);
    const pageView = this.renderingQueue.getHighestPriority(visiblePages, this._pages, scrollAhead, preRenderExtra, ignoreDetailViews);
    if (pageView) {
      this.#ensurePdfPageLoaded(pageView).then(() => {
        this.renderingQueue.renderView(pageView);
      });
      return true;
    }
    return false;
  }
  get hasEqualPageSizes() {
    const firstPageView = this._pages[0];
    for (let i = 1, ii = this._pages.length; i < ii; ++i) {
      const pageView = this._pages[i];
      if (pageView.width !== firstPageView.width || pageView.height !== firstPageView.height) {
        return false;
      }
    }
    return true;
  }
  getPagesOverview() {
    let initialOrientation;
    return this._pages.map(pageView => {
      const viewport = pageView.pdfPage.getViewport({
        scale: 1
      });
      const orientation = isPortraitOrientation(viewport);
      if (initialOrientation === undefined) {
        initialOrientation = orientation;
      } else if (this.enablePrintAutoRotate && orientation !== initialOrientation) {
        return {
          width: viewport.height,
          height: viewport.width,
          rotation: (viewport.rotation - 90) % 360
        };
      }
      return {
        width: viewport.width,
        height: viewport.height,
        rotation: viewport.rotation
      };
    });
  }
  get optionalContentConfigPromise() {
    if (!this.pdfDocument) {
      return Promise.resolve(null);
    }
    if (!this._optionalContentConfigPromise) {
      console.error("optionalContentConfigPromise: Not initialized yet.");
      return this.pdfDocument.getOptionalContentConfig({
        intent: "display"
      });
    }
    return this._optionalContentConfigPromise;
  }
  set optionalContentConfigPromise(promise) {
    if (!(promise instanceof Promise)) {
      throw new Error(`Invalid optionalContentConfigPromise: ${promise}`);
    }
    if (!this.pdfDocument) {
      return;
    }
    if (!this._optionalContentConfigPromise) {
      return;
    }
    this._optionalContentConfigPromise = promise;
    this.refresh(false, {
      optionalContentConfigPromise: promise
    });
    this.eventBus.dispatch("optionalcontentconfigchanged", {
      source: this,
      promise
    });
  }
  get scrollMode() {
    return this._scrollMode;
  }
  set scrollMode(mode) {
    if (this._scrollMode === mode) {
      return;
    }
    if (!isValidScrollMode(mode)) {
      throw new Error(`Invalid scroll mode: ${mode}`);
    }
    if (this.pagesCount > PagesCountLimit.FORCE_SCROLL_MODE_PAGE) {
      return;
    }
    this._previousScrollMode = this._scrollMode;
    this.clearSelection();
    this._scrollMode = mode;
    this.eventBus.dispatch("scrollmodechanged", {
      source: this,
      mode
    });
    this._updateScrollMode(this._currentPageNumber);
  }
  _updateScrollMode(pageNumber = null) {
    const scrollMode = this._scrollMode,
      viewer = this.viewer;
    viewer.classList.toggle("scrollHorizontal", scrollMode === ScrollMode.HORIZONTAL);
    viewer.classList.toggle("scrollWrapped", scrollMode === ScrollMode.WRAPPED);
    if (!this.pdfDocument || !pageNumber) {
      return;
    }
    if (scrollMode === ScrollMode.PAGE) {
      this.#ensurePageViewVisible();
    } else if (this._previousScrollMode === ScrollMode.PAGE) {
      this._updateSpreadMode();
    }
    if (this._currentScaleValue && isNaN(this._currentScaleValue)) {
      this.#setScale(this._currentScaleValue, {
        noScroll: true
      });
    }
    this._setCurrentPageNumber(pageNumber, true);
    this.update();
  }
  get spreadMode() {
    return this._spreadMode;
  }
  set spreadMode(mode) {
    if (this._spreadMode === mode) {
      return;
    }
    if (!isValidSpreadMode(mode)) {
      throw new Error(`Invalid spread mode: ${mode}`);
    }
    this.clearSelection();
    this._spreadMode = mode;
    this.eventBus.dispatch("spreadmodechanged", {
      source: this,
      mode
    });
    this._updateSpreadMode(this._currentPageNumber);
  }
  _updateSpreadMode(pageNumber = null) {
    if (!this.pdfDocument) {
      return;
    }
    const viewer = this.viewer,
      pages = this._pages;
    if (this._scrollMode === ScrollMode.PAGE) {
      this.#ensurePageViewVisible();
    } else {
      this.l10n.pause();
      viewer.textContent = "";
      if (this._spreadMode === SpreadMode.NONE) {
        for (const pageView of this._pages) {
          viewer.append(pageView.div);
        }
      } else {
        const parity = this._spreadMode - 1;
        let spread = null;
        for (let i = 0, ii = pages.length; i < ii; ++i) {
          if (spread === null) {
            spread = document.createElement("div");
            spread.className = "spread";
            viewer.append(spread);
          } else if (i % 2 === parity) {
            spread = spread.cloneNode(false);
            viewer.append(spread);
          }
          spread.append(pages[i].div);
        }
      }
      this.l10n.resume();
    }
    if (!pageNumber) {
      return;
    }
    if (this._currentScaleValue && isNaN(this._currentScaleValue)) {
      this.#setScale(this._currentScaleValue, {
        noScroll: true
      });
    }
    this._setCurrentPageNumber(pageNumber, true);
    this.update();
  }
  #getPageAdvance(currentPageNumber, previous = false) {
    switch (this._scrollMode) {
      case ScrollMode.WRAPPED:
        {
          const {
              views
            } = this._getVisiblePages(),
            pageLayout = new Map();
          for (const {
            id,
            y,
            percent,
            widthPercent
          } of views) {
            if (percent === 0 || widthPercent < 100) {
              continue;
            }
            pageLayout.getOrInsertComputed(y, makeArr).push(id);
          }
          for (const yArray of pageLayout.values()) {
            const currentIndex = yArray.indexOf(currentPageNumber);
            if (currentIndex === -1) {
              continue;
            }
            const numPages = yArray.length;
            if (numPages === 1) {
              break;
            }
            if (previous) {
              for (let i = currentIndex - 1, ii = 0; i >= ii; i--) {
                const currentId = yArray[i],
                  expectedId = yArray[i + 1] - 1;
                if (currentId < expectedId) {
                  return currentPageNumber - expectedId;
                }
              }
            } else {
              for (let i = currentIndex + 1; i < numPages; i++) {
                const currentId = yArray[i],
                  expectedId = yArray[i - 1] + 1;
                if (currentId > expectedId) {
                  return expectedId - currentPageNumber;
                }
              }
            }
            if (previous) {
              const firstId = yArray[0];
              if (firstId < currentPageNumber) {
                return currentPageNumber - firstId + 1;
              }
            } else {
              const lastId = yArray[numPages - 1];
              if (lastId > currentPageNumber) {
                return lastId - currentPageNumber + 1;
              }
            }
            break;
          }
          break;
        }
      case ScrollMode.HORIZONTAL:
        {
          break;
        }
      case ScrollMode.PAGE:
      case ScrollMode.VERTICAL:
        {
          if (this._spreadMode === SpreadMode.NONE) {
            break;
          }
          const parity = this._spreadMode - 1;
          if (previous && currentPageNumber % 2 !== parity) {
            break;
          } else if (!previous && currentPageNumber % 2 === parity) {
            break;
          }
          const {
              views
            } = this._getVisiblePages(),
            expectedId = previous ? currentPageNumber - 1 : currentPageNumber + 1;
          for (const {
            id,
            percent,
            widthPercent
          } of views) {
            if (id !== expectedId) {
              continue;
            }
            if (percent > 0 && widthPercent === 100) {
              return 2;
            }
            break;
          }
          break;
        }
    }
    return 1;
  }
  nextPage() {
    const currentPageNumber = this._currentPageNumber,
      pagesCount = this.pagesCount;
    if (currentPageNumber >= pagesCount) {
      return false;
    }
    const advance = this.#getPageAdvance(currentPageNumber, false) || 1;
    this.currentPageNumber = Math.min(currentPageNumber + advance, pagesCount);
    return true;
  }
  previousPage() {
    const currentPageNumber = this._currentPageNumber;
    if (currentPageNumber <= 1) {
      return false;
    }
    const advance = this.#getPageAdvance(currentPageNumber, true) || 1;
    this.currentPageNumber = Math.max(currentPageNumber - advance, 1);
    return true;
  }
  updateScale({
    drawingDelay,
    scaleFactor = null,
    steps = null,
    origin,
    pan = null
  }) {
    if (steps === null && scaleFactor === null) {
      throw new Error("Invalid updateScale options: either `steps` or `scaleFactor` must be provided.");
    }
    if (!this.pdfDocument) {
      return;
    }
    let newScale = this._currentScale;
    if (scaleFactor > 0 && scaleFactor !== 1) {
      newScale = Math.round(newScale * scaleFactor * 100) / 100;
    } else if (steps) {
      const delta = steps > 0 ? (/* inlined export .DEFAULT_SCALE_DELTA */1.1) : 1 / (/* inlined export .DEFAULT_SCALE_DELTA */1.1);
      const round = steps > 0 ? Math.ceil : Math.floor;
      steps = Math.abs(steps);
      do {
        newScale = round((newScale * delta).toFixed(2) * 10) / 10;
      } while (--steps > 0);
    }
    newScale = MathClamp(newScale, (/* inlined export .MIN_SCALE */0.1), (/* inlined export .MAX_SCALE */25));
    this.#setScale(newScale, {
      noScroll: false,
      drawingDelay,
      origin,
      pan
    });
  }
  increaseScale(options = {}) {
    this.updateScale({
      ...options,
      steps: options.steps ?? 1
    });
  }
  decreaseScale(options = {}) {
    this.updateScale({
      ...options,
      steps: -(options.steps ?? 1)
    });
  }
  #updateContainerHeightCss(height = this.container.clientHeight) {
    if (height !== this.#previousContainerHeight) {
      this.#previousContainerHeight = height;
      docStyle.setProperty("--viewer-container-height", `${height}px`);
    }
  }
  #resizeObserverCallback(entries) {
    for (const entry of entries) {
      if (entry.target === this.container) {
        this.#updateContainerHeightCss(Math.floor(entry.borderBoxSize[0].blockSize));
        this.#containerTopLeft = null;
        break;
      }
    }
  }
  get containerTopLeft() {
    return this.#containerTopLeft ||= [this.container.offsetTop, this.container.offsetLeft];
  }
  #cleanupTimeouts() {
    if (this.#scaleTimeoutId !== null) {
      clearTimeout(this.#scaleTimeoutId);
      this.#scaleTimeoutId = null;
    }
    if (this.#scrollTimeoutId !== null) {
      clearTimeout(this.#scrollTimeoutId);
      this.#scrollTimeoutId = null;
    }
  }
  #cleanupSwitchAnnotationEditorMode() {
    this.#switchAnnotationEditorModeAC?.abort();
    this.#switchAnnotationEditorModeAC = null;
    if (this.#switchAnnotationEditorModeTimeoutId !== null) {
      clearTimeout(this.#switchAnnotationEditorModeTimeoutId);
      this.#switchAnnotationEditorModeTimeoutId = null;
    }
  }
  #preloadEditingData(mode) {
    switch (mode) {
      case AnnotationEditorType.STAMP:
        this.#mlManager?.loadModel("altText");
        break;
      case AnnotationEditorType.SIGNATURE:
        this.#signatureManager?.loadSignatures();
        break;
    }
  }
  get annotationEditorMode() {
    return this.#annotationEditorUIManager ? this.#annotationEditorMode : AnnotationEditorType.DISABLE;
  }
  set annotationEditorMode({
    mode,
    editId = null,
    isFromKeyboard = false,
    mustEnterInEditMode = false,
    editComment = false
  }) {
    if (!this.#annotationEditorUIManager) {
      throw new Error(`The AnnotationEditor is not enabled.`);
    }
    if (this.#annotationEditorMode === mode) {
      return;
    }
    if (!isValidAnnotationEditorMode(mode)) {
      throw new Error(`Invalid AnnotationEditor mode: ${mode}`);
    }
    if (!this.pdfDocument) {
      return;
    }
    this.#preloadEditingData(mode);
    const {
      eventBus,
      pdfDocument
    } = this;
    const updater = async () => {
      this.#cleanupSwitchAnnotationEditorMode();
      this.#annotationEditorMode = mode;
      await this.#annotationEditorUIManager.updateMode(mode, editId, true, isFromKeyboard, mustEnterInEditMode, editComment);
      if (mode !== this.#annotationEditorMode || pdfDocument !== this.pdfDocument) {
        return;
      }
      eventBus.dispatch("annotationeditormodechanged", {
        source: this,
        mode
      });
    };
    if (mode === AnnotationEditorType.NONE || this.#annotationEditorMode === AnnotationEditorType.NONE) {
      const isEditing = mode !== AnnotationEditorType.NONE;
      if (!isEditing) {
        this.pdfDocument.annotationStorage.resetModifiedIds();
      }
      this.cleanup();
      for (const pageView of this._pages) {
        pageView.toggleEditingMode(isEditing);
      }
      const idsToRefresh = this.#switchToEditAnnotationMode();
      if (isEditing && idsToRefresh) {
        this.#cleanupSwitchAnnotationEditorMode();
        this.#switchAnnotationEditorModeAC = new AbortController();
        const signal = AbortSignal.any([this.#eventAC.signal, this.#switchAnnotationEditorModeAC.signal]);
        eventBus.on("pagerendered", ({
          pageNumber
        }) => {
          idsToRefresh.delete(pageNumber);
          if (idsToRefresh.size === 0) {
            this.#switchAnnotationEditorModeTimeoutId = setTimeout(updater, 0);
          }
        }, {
          signal,
          ...internalOpt
        });
        return;
      }
    }
    updater();
  }
  refresh(noUpdate = false, updateArgs = Object.create(null)) {
    if (!this.pdfDocument) {
      return;
    }
    for (const pageView of this._pages) {
      pageView.update(updateArgs);
    }
    this.#cleanupTimeouts();
    if (!noUpdate) {
      this.update();
    }
  }
}

;// ./web/secondary_toolbar.js



class SecondaryToolbar {
  #opts;
  constructor(options, eventBus) {
    this.#opts = options;
    const buttons = [{
      element: options.presentationModeButton,
      eventName: "presentationmode",
      close: true
    }, {
      element: options.printButton,
      eventName: "print",
      close: true
    }, {
      element: options.downloadButton,
      eventName: "download",
      close: true
    }, {
      element: options.viewBookmarkButton,
      eventName: null,
      close: true
    }, {
      element: options.firstPageButton,
      eventName: "firstpage",
      close: true
    }, {
      element: options.lastPageButton,
      eventName: "lastpage",
      close: true
    }, {
      element: options.pageRotateCwButton,
      eventName: "rotatecw",
      close: false
    }, {
      element: options.pageRotateCcwButton,
      eventName: "rotateccw",
      close: false
    }, {
      element: options.cursorSelectToolButton,
      eventName: "switchcursortool",
      eventDetails: {
        tool: CursorTool.SELECT
      },
      close: true
    }, {
      element: options.cursorHandToolButton,
      eventName: "switchcursortool",
      eventDetails: {
        tool: CursorTool.HAND
      },
      close: true
    }, {
      element: options.scrollPageButton,
      eventName: "switchscrollmode",
      eventDetails: {
        mode: ScrollMode.PAGE
      },
      close: true
    }, {
      element: options.scrollVerticalButton,
      eventName: "switchscrollmode",
      eventDetails: {
        mode: ScrollMode.VERTICAL
      },
      close: true
    }, {
      element: options.scrollHorizontalButton,
      eventName: "switchscrollmode",
      eventDetails: {
        mode: ScrollMode.HORIZONTAL
      },
      close: true
    }, {
      element: options.scrollWrappedButton,
      eventName: "switchscrollmode",
      eventDetails: {
        mode: ScrollMode.WRAPPED
      },
      close: true
    }, {
      element: options.spreadNoneButton,
      eventName: "switchspreadmode",
      eventDetails: {
        mode: SpreadMode.NONE
      },
      close: true
    }, {
      element: options.spreadOddButton,
      eventName: "switchspreadmode",
      eventDetails: {
        mode: SpreadMode.ODD
      },
      close: true
    }, {
      element: options.spreadEvenButton,
      eventName: "switchspreadmode",
      eventDetails: {
        mode: SpreadMode.EVEN
      },
      close: true
    }, {
      element: options.imageAltTextSettingsButton,
      eventName: "imagealttextsettings",
      close: true
    }, {
      element: options.documentPropertiesButton,
      eventName: "documentproperties",
      close: true
    }];
    buttons.push({
      element: options.openFileButton,
      eventName: "openfile",
      close: true
    });
    this.eventBus = eventBus;
    this.opened = false;
    this.#bindListeners(buttons);
    this.reset();
  }
  get isOpen() {
    return this.opened;
  }
  setPageNumber(pageNumber) {
    this.pageNumber = pageNumber;
    this.#updateUIState();
  }
  setPagesCount(pagesCount) {
    this.pagesCount = pagesCount;
    this.#updateUIState();
  }
  reset() {
    this.pageNumber = 0;
    this.pagesCount = 0;
    this.#updateUIState();
    this.eventBus.dispatch("switchcursortool", {
      source: this,
      reset: true
    });
    this.#scrollModeChanged({
      mode: ScrollMode.VERTICAL
    });
    this.#spreadModeChanged({
      mode: SpreadMode.NONE
    });
  }
  #updateUIState() {
    const {
      firstPageButton,
      lastPageButton,
      pageRotateCwButton,
      pageRotateCcwButton
    } = this.#opts;
    firstPageButton.disabled = this.pageNumber <= 1;
    lastPageButton.disabled = this.pageNumber >= this.pagesCount;
    pageRotateCwButton.disabled = this.pagesCount === 0;
    pageRotateCcwButton.disabled = this.pagesCount === 0;
  }
  #bindListeners(buttons) {
    const {
      eventBus
    } = this;
    const {
      toggleButton
    } = this.#opts;
    toggleButton.addEventListener("click", this.toggle.bind(this));
    for (const {
      element,
      eventName,
      close,
      eventDetails
    } of buttons) {
      element.addEventListener("click", evt => {
        if (eventName !== null) {
          eventBus.dispatch(eventName, {
            source: this,
            ...eventDetails
          });
        }
        if (close) {
          this.close();
        }
        eventBus.dispatch("reporttelemetry", {
          source: this,
          details: {
            type: "buttons",
            data: {
              id: element.id
            }
          }
        });
      });
    }
    eventBus.on("cursortoolchanged", this.#cursorToolChanged.bind(this), internalOpt);
    eventBus.on("scrollmodechanged", this.#scrollModeChanged.bind(this), internalOpt);
    eventBus.on("spreadmodechanged", this.#spreadModeChanged.bind(this), internalOpt);
  }
  #cursorToolChanged({
    tool,
    disabled
  }) {
    const {
      cursorSelectToolButton,
      cursorHandToolButton
    } = this.#opts;
    toggleCheckedBtn(cursorSelectToolButton, tool === CursorTool.SELECT);
    toggleCheckedBtn(cursorHandToolButton, tool === CursorTool.HAND);
    cursorSelectToolButton.disabled = disabled;
    cursorHandToolButton.disabled = disabled;
  }
  #scrollModeChanged({
    mode
  }) {
    const {
      scrollPageButton,
      scrollVerticalButton,
      scrollHorizontalButton,
      scrollWrappedButton,
      spreadNoneButton,
      spreadOddButton,
      spreadEvenButton
    } = this.#opts;
    toggleCheckedBtn(scrollPageButton, mode === ScrollMode.PAGE);
    toggleCheckedBtn(scrollVerticalButton, mode === ScrollMode.VERTICAL);
    toggleCheckedBtn(scrollHorizontalButton, mode === ScrollMode.HORIZONTAL);
    toggleCheckedBtn(scrollWrappedButton, mode === ScrollMode.WRAPPED);
    const forceScrollModePage = this.pagesCount > PagesCountLimit.FORCE_SCROLL_MODE_PAGE;
    scrollPageButton.disabled = forceScrollModePage;
    scrollVerticalButton.disabled = forceScrollModePage;
    scrollHorizontalButton.disabled = forceScrollModePage;
    scrollWrappedButton.disabled = forceScrollModePage;
    const isHorizontal = mode === ScrollMode.HORIZONTAL;
    spreadNoneButton.disabled = isHorizontal;
    spreadOddButton.disabled = isHorizontal;
    spreadEvenButton.disabled = isHorizontal;
  }
  #spreadModeChanged({
    mode
  }) {
    const {
      spreadNoneButton,
      spreadOddButton,
      spreadEvenButton
    } = this.#opts;
    toggleCheckedBtn(spreadNoneButton, mode === SpreadMode.NONE);
    toggleCheckedBtn(spreadOddButton, mode === SpreadMode.ODD);
    toggleCheckedBtn(spreadEvenButton, mode === SpreadMode.EVEN);
  }
  open() {
    if (this.opened) {
      return;
    }
    this.opened = true;
    const {
      toggleButton,
      toolbar
    } = this.#opts;
    toggleExpandedBtn(toggleButton, true, toolbar);
  }
  close() {
    if (!this.opened) {
      return;
    }
    this.opened = false;
    const {
      toggleButton,
      toolbar
    } = this.#opts;
    toggleExpandedBtn(toggleButton, false, toolbar);
  }
  toggle() {
    if (this.opened) {
      this.close();
    } else {
      this.open();
    }
  }
}

;// ./web/signature_manager.js


const DEFAULT_HEIGHT_IN_PAGE = 40;
class SignatureManager {
  #addButton;
  #tabsToAltText = null;
  #clearButton;
  #clearDescription;
  #currentEditor;
  #description;
  #dialog;
  #drawCurves = null;
  #drawPlaceholder;
  #drawPath = null;
  #drawPathString = "";
  #drawPoints = null;
  #drawSVG;
  #drawThickness;
  #errorBar;
  #errorDescription;
  #errorTitle;
  #extractedSignatureData = null;
  #imagePath = null;
  #imagePicker;
  #imagePickerLink;
  #imagePlaceholder;
  #imageSVG;
  #saveCheckbox;
  #saveContainer;
  #tabButtons;
  #addSignatureToolbarButton;
  #loadSignaturesPromise = null;
  #typeInput;
  #currentTab = null;
  #currentTabAC = null;
  #hasDescriptionChanged = false;
  #eventBus;
  #isStorageFull = false;
  #l10n;
  #overlayManager;
  #editDescriptionDialog;
  #signatureStorage;
  #uiManager = null;
  static #l10nDescription = null;
  constructor({
    dialog,
    panels,
    typeButton,
    typeInput,
    drawButton,
    drawPlaceholder,
    drawSVG,
    drawThickness,
    imageButton,
    imageSVG,
    imagePlaceholder,
    imagePicker,
    imagePickerLink,
    description,
    clearButton,
    cancelButton,
    addButton,
    errorCloseButton,
    errorBar,
    errorTitle,
    errorDescription,
    saveCheckbox,
    saveContainer
  }, editSignatureElements, addSignatureToolbarButton, overlayManager, l10n, signatureStorage, eventBus) {
    this.#addButton = addButton;
    this.#clearButton = clearButton;
    this.#clearDescription = description.lastElementChild;
    this.#description = description.firstElementChild;
    this.#dialog = dialog;
    this.#drawSVG = drawSVG;
    this.#drawPlaceholder = drawPlaceholder;
    this.#drawThickness = drawThickness;
    this.#errorBar = errorBar;
    this.#errorTitle = errorTitle;
    this.#errorDescription = errorDescription;
    this.#imageSVG = imageSVG;
    this.#imagePlaceholder = imagePlaceholder;
    this.#imagePicker = imagePicker;
    this.#imagePickerLink = imagePickerLink;
    this.#overlayManager = overlayManager;
    this.#saveCheckbox = saveCheckbox;
    this.#saveContainer = saveContainer;
    this.#addSignatureToolbarButton = addSignatureToolbarButton;
    this.#typeInput = typeInput;
    this.#l10n = l10n;
    this.#signatureStorage = signatureStorage;
    this.#eventBus = eventBus;
    this.#editDescriptionDialog = new EditDescriptionDialog(editSignatureElements, overlayManager);
    SignatureManager.#l10nDescription ||= Object.freeze({
      signature: "pdfjs-editor-add-signature-description-default-when-drawing",
      errorUploadTitle: "pdfjs-editor-add-signature-image-upload-error-title",
      errorUploadDescription: "pdfjs-editor-add-signature-image-upload-error-description",
      errorNoDataTitle: "pdfjs-editor-add-signature-image-no-data-error-title",
      errorNoDataDescription: "pdfjs-editor-add-signature-image-no-data-error-description"
    });
    dialog.addEventListener("close", this.#close.bind(this));
    dialog.addEventListener("contextmenu", e => {
      const {
        target
      } = e;
      if (target !== this.#typeInput && target !== this.#description) {
        e.preventDefault();
      }
    });
    dialog.addEventListener("drop", e => {
      stopEvent(e);
    });
    cancelButton.addEventListener("click", this.#cancel.bind(this));
    addButton.addEventListener("click", this.#add.bind(this));
    clearButton.addEventListener("click", () => {
      this.#reportTelemetry({
        type: "signature",
        action: "pdfjs.signature.clear",
        data: {
          type: this.#currentTab
        }
      });
      this.#initTab(null);
    }, {
      passive: true
    });
    this.#description.addEventListener("input", () => {
      this.#clearDescription.disabled = this.#description.value === "";
    }, {
      passive: true
    });
    this.#clearDescription.addEventListener("click", () => {
      this.#description.value = "";
      this.#clearDescription.disabled = true;
    }, {
      passive: true
    });
    errorCloseButton.addEventListener("click", () => {
      errorBar.hidden = true;
    }, {
      passive: true
    });
    this.#initTabButtons(typeButton, drawButton, imageButton, panels);
    imagePicker.accept = SupportedImageMimeTypes.keys().join(",");
    eventBus.on("storedsignatureschanged", this.#signaturesChanged.bind(this), internalOpt);
    overlayManager.register(dialog);
  }
  #initTabButtons(typeButton, drawButton, imageButton, panels) {
    const buttons = this.#tabButtons = new Map([["type", typeButton], ["draw", drawButton], ["image", imageButton]]);
    const tabCallback = e => {
      for (const [name, button] of buttons) {
        if (button === e.target) {
          button.setAttribute("aria-selected", true);
          button.setAttribute("tabindex", 0);
          panels.setAttribute("data-selected", name);
          this.#initTab(name);
        } else {
          button.setAttribute("aria-selected", false);
          button.setAttribute("tabindex", -1);
        }
      }
    };
    const buttonsArray = Array.from(buttons.values());
    for (let i = 0, ii = buttonsArray.length; i < ii; i++) {
      const button = buttonsArray[i];
      button.addEventListener("click", tabCallback, {
        passive: true
      });
      button.addEventListener("keydown", ({
        key
      }) => {
        if (key !== "ArrowLeft" && key !== "ArrowRight") {
          return;
        }
        buttonsArray[i + (key === "ArrowLeft" ? -1 : 1)]?.focus();
      }, {
        passive: true
      });
    }
  }
  #resetCommon() {
    this.#hasDescriptionChanged = false;
    this.#description.value = "";
    if (this.#currentTab) {
      this.#tabsToAltText.get(this.#currentTab).value = "";
    }
  }
  #resetTab(name) {
    switch (name) {
      case "type":
        this.#typeInput.value = "";
        break;
      case "draw":
        this.#drawCurves = null;
        this.#drawPoints = null;
        this.#drawPathString = "";
        this.#drawPath?.remove();
        this.#drawPath = null;
        this.#drawPlaceholder.hidden = false;
        this.#drawThickness.value = 1;
        break;
      case "image":
        this.#imagePlaceholder.hidden = false;
        this.#imagePath?.remove();
        this.#imagePath = null;
        break;
    }
  }
  #initTab(name) {
    if (name && this.#currentTab === name) {
      return;
    }
    if (this.#currentTab) {
      this.#tabsToAltText.get(this.#currentTab).value = this.#description.value;
    }
    if (name) {
      this.#currentTab = name;
    }
    this.#errorBar.hidden = true;
    const reset = !name;
    if (reset) {
      this.#resetCommon();
    } else {
      this.#description.value = this.#tabsToAltText.get(this.#currentTab).value;
    }
    this.#clearDescription.disabled = this.#description.value === "";
    this.#currentTabAC?.abort();
    this.#currentTabAC = new AbortController();
    switch (this.#currentTab) {
      case "type":
        this.#initTypeTab(reset);
        break;
      case "draw":
        this.#initDrawTab(reset);
        break;
      case "image":
        this.#initImageTab(reset);
        break;
    }
  }
  #disableButtons(value) {
    if (!value || !this.#isStorageFull) {
      this.#saveCheckbox.disabled = !value;
    }
    this.#clearButton.disabled = this.#addButton.disabled = this.#description.disabled = !value;
  }
  #initTypeTab(reset) {
    if (reset) {
      this.#resetTab("type");
    }
    this.#disableButtons(this.#typeInput.value);
    const {
      signal
    } = this.#currentTabAC;
    const options = {
      passive: true,
      signal
    };
    this.#typeInput.addEventListener("input", () => {
      const {
        value
      } = this.#typeInput;
      if (!this.#hasDescriptionChanged) {
        this.#tabsToAltText.get("type").default = this.#description.value = value;
        this.#clearDescription.disabled = value === "";
      }
      this.#disableButtons(value);
    }, options);
    this.#description.addEventListener("input", () => {
      this.#hasDescriptionChanged = this.#typeInput.value !== this.#description.value;
    }, options);
  }
  #initDrawTab(reset) {
    if (reset) {
      this.#resetTab("draw");
    }
    this.#disableButtons(this.#drawPath);
    const {
      signal
    } = this.#currentTabAC;
    const options = {
      signal
    };
    let currentPointerId = NaN;
    const drawCallback = e => {
      const {
        pointerId
      } = e;
      if (!isNaN(currentPointerId) && currentPointerId !== pointerId) {
        return;
      }
      currentPointerId = pointerId;
      e.preventDefault();
      this.#drawSVG.setPointerCapture(pointerId);
      const {
        width: drawWidth,
        height: drawHeight
      } = this.#drawSVG.getBoundingClientRect();
      let {
        offsetX,
        offsetY
      } = e;
      offsetX = Math.round(offsetX);
      offsetY = Math.round(offsetY);
      if (e.target === this.#drawPlaceholder) {
        this.#drawPlaceholder.hidden = true;
      }
      if (!this.#drawCurves) {
        this.#drawCurves = {
          width: drawWidth,
          height: drawHeight,
          thickness: parseInt(this.#drawThickness.value, 10),
          curves: []
        };
        this.#disableButtons(true);
        const svgFactory = new DOMSVGFactory();
        const path = this.#drawPath = svgFactory.createElement("path");
        path.setAttribute("stroke-width", this.#drawThickness.value);
        this.#drawSVG.append(path);
        this.#drawSVG.addEventListener("pointerdown", drawCallback, options);
        this.#drawPlaceholder.removeEventListener("pointerdown", drawCallback);
        if (this.#description.value === "") {
          this.#l10n.get(SignatureManager.#l10nDescription.signature).then(description => {
            this.#tabsToAltText.get("draw").default = description;
            this.#description.value ||= description;
            this.#clearDescription.disabled = this.#description.value === "";
          });
        }
      }
      this.#drawPoints = [offsetX, offsetY];
      this.#drawCurves.curves.push({
        points: this.#drawPoints
      });
      this.#drawPathString += `M ${offsetX} ${offsetY}`;
      this.#drawPath.setAttribute("d", this.#drawPathString);
      const finishDrawAC = new AbortController();
      const listenerDrawOptions = {
        signal: AbortSignal.any([signal, finishDrawAC.signal])
      };
      this.#drawSVG.addEventListener("contextmenu", noContextMenu, listenerDrawOptions);
      this.#drawSVG.addEventListener("pointermove", evt => {
        evt.preventDefault();
        let {
          offsetX: x,
          offsetY: y
        } = evt;
        x = Math.round(x);
        y = Math.round(y);
        const drawPoints = this.#drawPoints;
        if (x < 0 || y < 0 || x > drawWidth || y > drawHeight || x === drawPoints.at(-2) && y === drawPoints.at(-1)) {
          return;
        }
        if (drawPoints.length >= 4) {
          const [x1, y1, x2, y2] = drawPoints.slice(-4);
          this.#drawPathString += `C${(x1 + 5 * x2) / 6} ${(y1 + 5 * y2) / 6} ${(5 * x2 + x) / 6} ${(5 * y2 + y) / 6} ${(x2 + x) / 2} ${(y2 + y) / 2}`;
        } else {
          this.#drawPathString += `L${x} ${y}`;
        }
        drawPoints.push(x, y);
        this.#drawPath.setAttribute("d", this.#drawPathString);
      }, listenerDrawOptions);
      this.#drawSVG.addEventListener("pointerup", evt => {
        const {
          pointerId: pId
        } = evt;
        if (!isNaN(currentPointerId) && currentPointerId !== pId) {
          return;
        }
        currentPointerId = NaN;
        evt.preventDefault();
        this.#drawSVG.releasePointerCapture(pId);
        finishDrawAC.abort();
        if (this.#drawPoints.length === 2) {
          this.#drawPathString += `L${this.#drawPoints[0]} ${this.#drawPoints[1]}`;
          this.#drawPath.setAttribute("d", this.#drawPathString);
        }
      }, listenerDrawOptions);
    };
    if (this.#drawCurves) {
      this.#drawSVG.addEventListener("pointerdown", drawCallback, options);
    } else {
      this.#drawPlaceholder.addEventListener("pointerdown", drawCallback, options);
    }
    this.#drawThickness.addEventListener("input", () => {
      const {
        value: thickness
      } = this.#drawThickness;
      this.#drawThickness.setAttribute("data-l10n-args", JSON.stringify({
        thickness
      }));
      if (!this.#drawCurves) {
        return;
      }
      this.#drawPath.setAttribute("stroke-width", thickness);
      this.#drawCurves.thickness = thickness;
    }, options);
  }
  #showError(type) {
    this.#errorTitle.setAttribute("data-l10n-id", SignatureManager.#l10nDescription[`error${type}Title`]);
    this.#errorDescription.setAttribute("data-l10n-id", SignatureManager.#l10nDescription[`error${type}Description`]);
    this.#errorBar.hidden = false;
  }
  #initImageTab(reset) {
    if (reset) {
      this.#resetTab("image");
    }
    this.#disableButtons(this.#imagePath);
    const {
      signal
    } = this.#currentTabAC;
    const options = {
      signal
    };
    const passiveOptions = {
      passive: true,
      signal
    };
    this.#imagePickerLink.addEventListener("keydown", e => {
      const {
        key
      } = e;
      if (key === "Enter" || key === " ") {
        stopEvent(e);
        this.#imagePicker.click();
      }
    }, options);
    this.#imagePicker.addEventListener("click", () => {
      this.#dialog.classList.toggle("waiting", true);
    }, passiveOptions);
    this.#imagePicker.addEventListener("change", async () => {
      const file = this.#imagePicker.files?.[0];
      if (!file || !SupportedImageMimeTypes.has(file.type)) {
        this.#showError("Upload");
        this.#dialog.classList.toggle("waiting", false);
        return;
      }
      await this.#extractSignature(file);
    }, passiveOptions);
    this.#imagePicker.addEventListener("cancel", () => {
      this.#dialog.classList.toggle("waiting", false);
    }, passiveOptions);
    this.#imagePlaceholder.addEventListener("dragover", e => {
      const {
        dataTransfer
      } = e;
      for (const {
        type
      } of dataTransfer.items) {
        if (!SupportedImageMimeTypes.has(type)) {
          continue;
        }
        dataTransfer.dropEffect = dataTransfer.effectAllowed === "copy" ? "copy" : "move";
        stopEvent(e);
        return;
      }
      dataTransfer.dropEffect = "none";
    }, options);
    this.#imagePlaceholder.addEventListener("drop", e => {
      const {
        dataTransfer: {
          files
        }
      } = e;
      if (!files?.length) {
        return;
      }
      for (const file of files) {
        if (SupportedImageMimeTypes.has(file.type)) {
          this.#extractSignature(file);
          break;
        }
      }
      stopEvent(e);
      this.#dialog.classList.toggle("waiting", true);
    }, options);
  }
  async #extractSignature(file) {
    let data;
    try {
      data = await this.#uiManager.imageManager.getFromFile(file);
    } catch (e) {
      console.error("SignatureManager.#extractSignature.", e);
    }
    if (!data) {
      this.#showError("Upload");
      this.#dialog.classList.toggle("waiting", false);
      return;
    }
    const lineData = this.#extractedSignatureData = this.#currentEditor.getFromImage(data.bitmap);
    if (!lineData) {
      this.#showError("NoData");
      this.#dialog.classList.toggle("waiting", false);
      return;
    }
    const {
      outline
    } = lineData;
    this.#imagePlaceholder.hidden = true;
    this.#disableButtons(true);
    const svgFactory = new DOMSVGFactory();
    const path = this.#imagePath = svgFactory.createElement("path");
    this.#imageSVG.setAttribute("viewBox", outline.viewBox);
    this.#imageSVG.setAttribute("preserveAspectRatio", "xMidYMid meet");
    this.#imageSVG.append(path);
    path.setAttribute("d", outline.toSVGPath());
    this.#tabsToAltText.get("image").default = file.name;
    if (this.#description.value === "") {
      this.#description.value = file.name || "";
      this.#clearDescription.disabled = this.#description.value === "";
    }
    this.#dialog.classList.toggle("waiting", false);
  }
  #getOutlineForType() {
    return this.#currentEditor.getFromText(this.#typeInput.value, window.getComputedStyle(this.#typeInput));
  }
  #getOutlineForDraw() {
    const {
      width,
      height
    } = this.#drawSVG.getBoundingClientRect();
    return this.#currentEditor.getDrawnSignature(this.#drawCurves, width, height);
  }
  #reportTelemetry(data) {
    this.#eventBus.dispatch("reporttelemetry", {
      source: this,
      details: {
        type: "editing",
        data
      }
    });
  }
  #addToolbarButton(signatureData, uuid, description) {
    const {
      curves,
      areContours,
      thickness,
      width,
      height
    } = signatureData;
    const maxDim = Math.max(width, height);
    const outlineData = SignatureExtractor.processDrawnLines({
      lines: {
        curves,
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
    if (!outlineData) {
      return;
    }
    const {
      outline
    } = outlineData;
    const svgFactory = new DOMSVGFactory();
    const div = document.createElement("div");
    const button = document.createElement("button");
    button.addEventListener("click", () => {
      this.#eventBus.dispatch("switchannotationeditorparams", {
        source: this,
        type: AnnotationEditorParamsType.CREATE,
        value: {
          signatureData: {
            lines: {
              curves,
              thickness,
              width,
              height
            },
            mustSmooth: false,
            areContours,
            description,
            uuid,
            heightInPage: DEFAULT_HEIGHT_IN_PAGE
          }
        }
      });
    });
    div.append(button);
    div.classList.add("toolbarAddSignatureButtonContainer");
    const svg = svgFactory.create(1, 1, true);
    button.append(svg);
    const span = document.createElement("span");
    span.ariaHidden = true;
    button.append(span);
    button.classList.add("toolbarAddSignatureButton");
    button.type = "button";
    span.textContent = description;
    button.setAttribute("data-l10n-id", "pdfjs-editor-add-saved-signature-button");
    button.setAttribute("data-l10n-args", JSON.stringify({
      description
    }));
    button.tabIndex = 0;
    const path = svgFactory.createElement("path");
    svg.append(path);
    svg.setAttribute("viewBox", outline.viewBox);
    svg.setAttribute("preserveAspectRatio", "xMidYMid meet");
    if (areContours) {
      path.classList.add("contours");
    }
    path.setAttribute("d", outline.toSVGPath());
    const deleteButton = document.createElement("button");
    div.append(deleteButton);
    deleteButton.classList.add("toolbarButton", "deleteButton");
    deleteButton.setAttribute("data-l10n-id", "pdfjs-editor-delete-signature-button1");
    deleteButton.type = "button";
    deleteButton.tabIndex = 0;
    deleteButton.addEventListener("click", async () => {
      if (await this.#signatureStorage.delete(uuid)) {
        div.remove();
        this.#reportTelemetry({
          type: "signature",
          action: "pdfjs.signature.delete_saved",
          data: {
            savedCount: await this.#signatureStorage.size()
          }
        });
      }
    });
    const deleteSpan = document.createElement("span");
    deleteButton.append(deleteSpan);
    deleteSpan.setAttribute("data-l10n-id", "pdfjs-editor-delete-signature-button-label1");
    this.#addSignatureToolbarButton.before(div);
  }
  async #signaturesChanged() {
    const parent = this.#addSignatureToolbarButton.parentElement;
    while (parent.firstElementChild !== this.#addSignatureToolbarButton) {
      parent.firstElementChild.remove();
    }
    this.#loadSignaturesPromise = null;
    await this.loadSignatures(true);
  }
  getSignature(params) {
    return this.open(params);
  }
  async loadSignatures(reload = false) {
    if (!this.#addSignatureToolbarButton || !reload && this.#addSignatureToolbarButton.previousElementSibling || !this.#signatureStorage) {
      return;
    }
    if (!this.#loadSignaturesPromise) {
      this.#loadSignaturesPromise = this.#signatureStorage.getAll().then(async signatures => [signatures, await Promise.all(Array.from(signatures.values(), ({
        signatureData
      }) => SignatureExtractor.decompressSignature(signatureData)))]);
      if (!reload) {
        return;
      }
    }
    const [signatures, signaturesData] = await this.#loadSignaturesPromise;
    this.#loadSignaturesPromise = null;
    let i = 0;
    for (const [uuid, {
      description
    }] of signatures) {
      const data = signaturesData[i++];
      if (!data) {
        continue;
      }
      data.curves = data.outlines.map(points => ({
        points
      }));
      delete data.outlines;
      this.#addToolbarButton(data, uuid, description);
    }
  }
  async renderEditButton(editor) {
    const button = document.createElement("button");
    button.classList.add("altText", "editDescription");
    button.tabIndex = 0;
    if (editor.description) {
      button.title = editor.description;
    }
    const span = document.createElement("span");
    button.append(span);
    span.setAttribute("data-l10n-id", "pdfjs-editor-add-signature-edit-button-label");
    button.addEventListener("click", () => {
      this.#editDescriptionDialog.open(editor);
    }, {
      passive: true
    });
    return button;
  }
  async open({
    uiManager,
    editor
  }) {
    this.#tabsToAltText ||= new Map(this.#tabButtons.keys().map(name => [name, {
      value: "",
      default: ""
    }]));
    this.#uiManager = uiManager;
    this.#currentEditor = editor;
    this.#uiManager.removeEditListeners();
    const isStorageFull = this.#isStorageFull = await this.#signatureStorage.isFull();
    this.#saveContainer.classList.toggle("fullStorage", isStorageFull);
    this.#saveCheckbox.checked = !isStorageFull;
    await this.#overlayManager.open(this.#dialog);
    const tabType = this.#tabButtons.get("type");
    tabType.focus();
    tabType.click();
  }
  #cancel() {
    this.#finish();
  }
  #finish() {
    this.#overlayManager.closeIfActive(this.#dialog);
  }
  #close() {
    if (this.#currentEditor._drawId === null) {
      this.#currentEditor.remove();
    }
    this.#uiManager?.addEditListeners();
    this.#currentTabAC?.abort();
    this.#currentTabAC = null;
    this.#uiManager = null;
    this.#currentEditor = null;
    this.#resetCommon();
    for (const [name] of this.#tabButtons) {
      this.#resetTab(name);
    }
    this.#disableButtons(false);
    this.#currentTab = null;
    this.#tabsToAltText = null;
  }
  async #add() {
    let data;
    const type = this.#currentTab;
    switch (type) {
      case "type":
        data = this.#getOutlineForType();
        break;
      case "draw":
        data = this.#getOutlineForDraw();
        break;
      case "image":
        data = this.#extractedSignatureData;
        break;
    }
    let uuid = null;
    const description = this.#description.value;
    if (this.#saveCheckbox.checked) {
      const {
        newCurves,
        areContours,
        thickness,
        width,
        height
      } = data;
      const signatureData = await SignatureExtractor.compressSignature({
        outlines: newCurves,
        areContours,
        thickness,
        width,
        height
      });
      uuid = await this.#signatureStorage.create({
        description,
        signatureData
      });
      if (uuid) {
        this.#addToolbarButton({
          curves: newCurves.map(points => ({
            points
          })),
          areContours,
          thickness,
          width,
          height
        }, uuid, description);
      } else {
        console.warn("SignatureManager.add: cannot save the signature.");
      }
    }
    const altText = this.#tabsToAltText.get(type);
    this.#reportTelemetry({
      type: "signature",
      action: "pdfjs.signature.created",
      data: {
        type,
        saved: !!uuid,
        savedCount: await this.#signatureStorage.size(),
        descriptionChanged: description !== altText.default
      }
    });
    this.#currentEditor.addSignature(data, DEFAULT_HEIGHT_IN_PAGE, this.#description.value, uuid);
    this.#finish();
  }
  destroy() {
    this.#uiManager = null;
    this.#finish();
  }
}
class EditDescriptionDialog {
  #currentEditor;
  #previousDescription;
  #description;
  #dialog;
  #overlayManager;
  #signatureSVG;
  #uiManager;
  constructor({
    dialog,
    description,
    cancelButton,
    updateButton,
    editSignatureView
  }, overlayManager) {
    const descriptionInput = this.#description = description.firstElementChild;
    this.#signatureSVG = editSignatureView;
    this.#dialog = dialog;
    this.#overlayManager = overlayManager;
    dialog.addEventListener("close", this.#close.bind(this));
    dialog.addEventListener("contextmenu", e => {
      if (e.target !== this.#description) {
        e.preventDefault();
      }
    });
    cancelButton.addEventListener("click", this.#cancel.bind(this));
    updateButton.addEventListener("click", this.#update.bind(this));
    const clearDescription = description.lastElementChild;
    clearDescription.addEventListener("click", () => {
      descriptionInput.value = "";
      clearDescription.disabled = true;
      updateButton.disabled = this.#previousDescription === "";
    });
    descriptionInput.addEventListener("input", () => {
      const {
        value
      } = descriptionInput;
      clearDescription.disabled = value === "";
      updateButton.disabled = value === this.#previousDescription;
      editSignatureView.setAttribute("aria-label", value);
    }, {
      passive: true
    });
    overlayManager.register(dialog);
  }
  async open(editor) {
    this.#uiManager = editor._uiManager;
    this.#currentEditor = editor;
    this.#previousDescription = this.#description.value = editor.description;
    this.#description.dispatchEvent(new Event("input"));
    this.#uiManager.removeEditListeners();
    const {
      areContours,
      outline
    } = editor.getSignaturePreview();
    const svgFactory = new DOMSVGFactory();
    const path = svgFactory.createElement("path");
    this.#signatureSVG.append(path);
    this.#signatureSVG.setAttribute("viewBox", outline.viewBox);
    path.setAttribute("d", outline.toSVGPath());
    if (areContours) {
      path.classList.add("contours");
    }
    await this.#overlayManager.open(this.#dialog);
  }
  async #update() {
    this.#currentEditor._reportTelemetry({
      action: "pdfjs.signature.edit_description",
      data: {
        hasBeenChanged: true
      }
    });
    this.#currentEditor.description = this.#description.value;
    this.#finish();
  }
  #cancel() {
    this.#currentEditor._reportTelemetry({
      action: "pdfjs.signature.edit_description",
      data: {
        hasBeenChanged: false
      }
    });
    this.#finish();
  }
  #finish() {
    this.#overlayManager.closeIfActive(this.#dialog);
  }
  #close() {
    this.#uiManager?.addEditListeners();
    this.#uiManager = null;
    this.#currentEditor = null;
    this.#signatureSVG.firstElementChild.remove();
  }
}

;// ./web/digital_signature_properties_manager.js

const STATUS_ROW_VERIFIED = "pdfjs-digital-signature-properties-status-verified";
const STATUS_ROW_INVALID = "pdfjs-digital-signature-properties-status-invalid";
const STATUS_ROW_UNKNOWN = "pdfjs-digital-signature-properties-status-unknown";
const STATUS_INFO = {
  verified: {
    priority: 0,
    severity: "verified",
    bannerId: "pdfjs-digital-signature-properties-banner-verified",
    statusId: STATUS_ROW_VERIFIED
  },
  unknown: {
    priority: 1,
    severity: "error",
    bannerId: "pdfjs-digital-signature-properties-banner-unknown",
    statusId: STATUS_ROW_UNKNOWN
  },
  untrusted: {
    priority: 2,
    severity: "warn",
    bannerId: "pdfjs-digital-signature-properties-banner-untrusted",
    statusId: STATUS_ROW_VERIFIED
  },
  expired: {
    priority: 3,
    severity: "warn",
    bannerId: "pdfjs-digital-signature-properties-banner-expired",
    statusId: STATUS_ROW_VERIFIED
  },
  revoked: {
    priority: 4,
    severity: "error",
    bannerId: "pdfjs-digital-signature-properties-banner-revoked",
    statusId: STATUS_ROW_VERIFIED
  },
  invalid: {
    priority: 5,
    severity: "error",
    bannerId: "pdfjs-digital-signature-properties-banner-invalid",
    statusId: STATUS_ROW_INVALID
  }
};
const CERT_L10N_IDS = {
  trusted: "pdfjs-digital-signature-properties-certificate-trusted",
  unknown: "pdfjs-digital-signature-properties-certificate-unknown",
  untrusted: "pdfjs-digital-signature-properties-certificate-untrusted",
  expired: "pdfjs-digital-signature-properties-certificate-expired",
  revoked: "pdfjs-digital-signature-properties-certificate-revoked"
};
const CERT_EXPIRED_WITH_DATE_L10N_ID = "pdfjs-digital-signature-properties-certificate-expired-with-date";
function untrustedCertLabel(errorCode, issuerCN) {
  const code = (errorCode || "").toUpperCase();
  const args = issuerCN ? {
    issuer: issuerCN
  } : null;
  if (code.includes("UNKNOWN_ISSUER") && args) {
    return {
      id: "pdfjs-digital-signature-properties-certificate-untrusted-unknown-issuer",
      args
    };
  }
  if (code.includes("SELF_SIGNED") && args) {
    return {
      id: "pdfjs-digital-signature-properties-certificate-untrusted-self-signed",
      args
    };
  }
  if (code.includes("UNTRUSTED_ISSUER") && args) {
    return {
      id: "pdfjs-digital-signature-properties-certificate-untrusted-untrusted-issuer",
      args
    };
  }
  return {
    id: "pdfjs-digital-signature-properties-certificate-untrusted",
    args: null
  };
}
function expirationDateForCert(cert) {
  if (!cert) {
    return null;
  }
  const now = Date.now();
  const entries = Array.isArray(cert.chain) && cert.chain.length ? cert.chain : [cert];
  for (const entry of entries) {
    if (typeof entry?.notAfter !== "string" || !entry.notAfter) {
      continue;
    }
    const date = new Date(entry.notAfter);
    const ts = date.getTime();
    if (Number.isFinite(ts) && ts < now) {
      return date;
    }
  }
  return null;
}
class SignaturePropertiesManager {
  #appConfig;
  #verifier;
  #eventBus;
  #signatures = [];
  #results = new Map();
  #pendingVerify = new Set();
  #isOpen = false;
  #isLoading = false;
  #needsRender = false;
  #pdfDocument = null;
  constructor({
    appConfig,
    verifier,
    eventBus
  }) {
    this.#appConfig = appConfig;
    this.#verifier = verifier;
    this.#eventBus = eventBus;
    const button = appConfig.signaturePropertiesButton;
    for (let i = 0; i < 3; i++) {
      const dot = document.createElement("span");
      dot.className = "loadingDot";
      button.append(dot);
    }
    button.addEventListener("click", () => {
      this.#toggle();
    });
  }
  get isOpen() {
    return this.#isOpen;
  }
  close() {
    if (this.#isOpen) {
      this.#close();
    }
  }
  shouldCloseOnClick(target) {
    if (!this.#isOpen) {
      return false;
    }
    return !(this.#appConfig.signaturePropertiesButton.contains(target) || this.#appConfig.signaturePropertiesPanel.contains(target));
  }
  async setDocument(pdfDocument) {
    if (this.#pdfDocument) {
      this.#signatures = [];
      this.#results.clear();
      this.#pendingVerify.clear();
      this.#needsRender = false;
      this.#hideButton();
      this.#close();
      this.#updateButtonState();
    }
    this.#pdfDocument = pdfDocument;
    if (!pdfDocument) {
      return;
    }
    this.#isLoading = true;
    this.#render();
    let signatures;
    try {
      signatures = await pdfDocument.getSignatures();
    } catch (ex) {
      console.warn("getSignatures failed:", ex);
    }
    if (pdfDocument !== this.#pdfDocument) {
      return;
    }
    this.#signatures = signatures || [];
    this.#isLoading = false;
    if (this.#signatures.length === 0) {
      this.#hideButton();
      return;
    }
    this.#showButton();
    for (const sig of this.#signatures) {
      this.#results.set(sig.id, {
        status: "unknown",
        errorCode: null,
        message: null,
        certificate: null,
        documentModifiedAfterSigning: !sig.coversWholeDocument,
        modificationsAfterSignature: sig.modificationsAfterSignature
      });
    }
    this.#render();
    this.#updateButtonState();
    for (const sig of this.#signatures) {
      this.#verify(sig, pdfDocument);
    }
  }
  #showButton() {
    const root = this.#appConfig.signaturePropertiesButton.parentElement;
    if (root) {
      root.hidden = false;
    }
    const sep = this.#appConfig.signaturePropertiesSeparator;
    if (sep) {
      sep.hidden = false;
    }
  }
  #hideButton() {
    const root = this.#appConfig.signaturePropertiesButton.parentElement;
    if (root) {
      root.hidden = true;
    }
    const sep = this.#appConfig.signaturePropertiesSeparator;
    if (sep) {
      sep.hidden = true;
    }
  }
  #toggle() {
    if (this.#isOpen) {
      this.#close();
    } else {
      this.#open();
    }
  }
  #open() {
    this.#isOpen = true;
    this.#eventBus?.dispatch("switchannotationeditormode", {
      source: this,
      mode: AnnotationEditorType.NONE
    });
    this.#eventBus?.dispatch("findbarclose", {
      source: this
    });
    this.#appConfig.signaturePropertiesPanel.classList.remove("hidden");
    this.#appConfig.signaturePropertiesButton.setAttribute("aria-expanded", "true");
    if (this.#needsRender) {
      this.#render();
    }
  }
  #close() {
    this.#isOpen = false;
    this.#appConfig.signaturePropertiesPanel.classList.add("hidden");
    this.#appConfig.signaturePropertiesButton.setAttribute("aria-expanded", "false");
  }
  get #worst() {
    let worst = "verified";
    for (const r of this.#results.values()) {
      if (r?.status && STATUS_INFO[r.status].priority > STATUS_INFO[worst].priority) {
        worst = r.status;
      }
    }
    return worst;
  }
  get #bannerState() {
    if (this.#results.size === 0) {
      return {
        worst: "unknown",
        severity: "error",
        count: 0
      };
    }
    const worst = this.#worst;
    let count = 0;
    for (const r of this.#results.values()) {
      if (r?.status === worst) {
        count++;
      }
    }
    return {
      worst,
      severity: STATUS_INFO[worst].severity,
      count
    };
  }
  #render() {
    if (!this.#isOpen) {
      this.#needsRender = true;
      return;
    }
    this.#needsRender = false;
    const list = this.#appConfig.signaturePropertiesList;
    const banner = this.#appConfig.signaturePropertiesBanner;
    const fragment = document.createDocumentFragment();
    if (this.#isLoading) {
      banner.hidden = true;
      list.replaceChildren();
      return;
    }
    const {
      worst,
      severity,
      count
    } = this.#bannerState;
    banner.replaceChildren();
    banner.hidden = false;
    banner.className = `sigBanner ${severity}`;
    banner.setAttribute("data-l10n-id", STATUS_INFO[worst].bannerId);
    banner.setAttribute("data-l10n-args", JSON.stringify({
      count
    }));
    const byParent = new Map();
    const topLevel = [];
    for (const sig of this.#signatures) {
      if (sig.parentId) {
        byParent.getOrInsertComputed(sig.parentId, makeArr).push(sig);
      } else {
        topLevel.push(sig);
      }
    }
    const everythingFine = severity === "verified";
    for (const sig of topLevel) {
      fragment.append(this.#renderCard(sig, byParent, 0, everythingFine));
    }
    list.replaceChildren(fragment);
  }
  #renderCard(sig, byParent, depth, everythingFine) {
    const subs = byParent.get(sig.id) || [];
    const li = document.createElement("li");
    li.classList.add("sigCard");
    if (depth === 0 && everythingFine) {
      li.classList.add("sigCard--top-allfine");
    }
    const result = this.#results.get(sig.id);
    const subjectCN = result?.certificate?.subjectCN;
    if (subjectCN) {
      const signer = document.createElement("div");
      signer.className = "signer";
      signer.textContent = subjectCN;
      li.append(signer);
    }
    const statusRow = document.createElement("div");
    statusRow.classList.add("row", `status--${result.status}`);
    const statusLabel = document.createElement("span");
    statusLabel.setAttribute("data-l10n-id", STATUS_INFO[result.status].statusId);
    statusRow.append(statusLabel);
    li.append(statusRow);
    if (result.status === "invalid" && result.message) {
      const reason = document.createElement("div");
      reason.className = "detail";
      reason.setAttribute("data-l10n-id", "pdfjs-digital-signature-properties-reason");
      reason.setAttribute("data-l10n-args", JSON.stringify({
        reason: result.message
      }));
      li.append(reason);
    }
    const cert = result.certificate;
    let certKind = "unknown";
    if (cert) {
      switch (result.status) {
        case "verified":
          certKind = "trusted";
          break;
        case "expired":
          certKind = "expired";
          break;
        case "revoked":
          certKind = "revoked";
          break;
        case "untrusted":
          certKind = "untrusted";
          break;
        default:
          certKind = "unknown";
      }
    }
    if (result.status !== "invalid") {
      const certRow = document.createElement("div");
      certRow.classList.add("row", `cert--${certKind}`);
      const certLabel = document.createElement("span");
      let l10nId = CERT_L10N_IDS[certKind];
      let l10nArgs = null;
      if (cert?.issuerCN && certKind === "trusted") {
        l10nArgs = {
          issuer: cert.issuerCN
        };
      } else if (certKind === "expired") {
        const date = expirationDateForCert(cert);
        if (date) {
          l10nId = CERT_EXPIRED_WITH_DATE_L10N_ID;
          l10nArgs = {
            dateObj: date.valueOf()
          };
        }
      } else if (certKind === "untrusted") {
        const label = untrustedCertLabel(result.errorCode, cert?.issuerCN);
        l10nId = label.id;
        l10nArgs = label.args;
      }
      certLabel.setAttribute("data-l10n-id", l10nId);
      if (l10nArgs) {
        certLabel.setAttribute("data-l10n-args", JSON.stringify(l10nArgs));
      }
      certRow.append(certLabel);
      li.append(certRow);
    }
    if (result.status === "untrusted" && result.message) {
      const detail = document.createElement("div");
      detail.className = "detail";
      detail.textContent = result.message;
      li.append(detail);
    }
    if (result.status === "expired" && result.message) {
      const detail = document.createElement("div");
      detail.className = "detail";
      detail.textContent = result.message;
      li.append(detail);
    }
    const signingDate = PDFDateString.toDateObject(sig.signingTime);
    if (signingDate) {
      const ts = document.createElement("div");
      ts.className = "detail";
      ts.setAttribute("data-l10n-id", "pdfjs-digital-signature-properties-timestamp");
      ts.setAttribute("data-l10n-args", JSON.stringify({
        dateObj: signingDate.valueOf()
      }));
      li.append(ts);
    }
    if (cert && typeof this.#verifier?.viewCertificate === "function") {
      const viewCert = document.createElement("button");
      viewCert.className = "viewCert";
      viewCert.type = "button";
      viewCert.setAttribute("data-l10n-id", "pdfjs-digital-signature-properties-view-certificate");
      viewCert.addEventListener("click", e => {
        e.stopPropagation();
        this.#verifier.viewCertificate(cert);
      });
      li.append(viewCert);
    }
    if (subs.length > 0) {
      const subList = document.createElement("ul");
      subList.classList.add("signaturePropertiesList", "nested");
      for (const sub of subs) {
        subList.append(this.#renderCard(sub, byParent, depth + 1, everythingFine));
      }
      if (depth === 0) {
        const details = document.createElement("details");
        details.className = "subSignatures";
        details.open = true;
        const summary = document.createElement("summary");
        summary.setAttribute("data-l10n-id", "pdfjs-digital-signature-properties-sub-signatures");
        summary.setAttribute("data-l10n-args", JSON.stringify({
          count: this.#countDescendants(sig.id, byParent)
        }));
        details.append(summary);
        details.append(subList);
        li.append(details);
      } else {
        li.append(subList);
      }
    }
    return li;
  }
  #countDescendants(id, byParent) {
    const direct = byParent.get(id);
    if (!direct) {
      return 0;
    }
    let total = direct.length;
    for (const sub of direct) {
      total += this.#countDescendants(sub.id, byParent);
    }
    return total;
  }
  async #verify(signature, pdfDocument) {
    if (!this.#verifier || this.#pendingVerify.has(signature.id)) {
      return;
    }
    this.#pendingVerify.add(signature.id);
    this.#render();
    let result;
    try {
      const bytes = await pdfDocument.getSignatureData(signature.id);
      if (pdfDocument !== this.#pdfDocument) {
        return;
      }
      if (!bytes) {
        throw new Error("missing signature data");
      }
      result = await this.#verifier.verify({
        ...signature,
        ...bytes
      });
    } catch (ex) {
      console.warn("signature verify failed:", ex);
      result = {
        status: "unknown",
        errorCode: "BRIDGE_ERROR",
        message: ex?.message ?? null,
        certificate: null,
        documentModifiedAfterSigning: !signature.coversWholeDocument,
        modificationsAfterSignature: signature.modificationsAfterSignature
      };
    }
    this.#pendingVerify.delete(signature.id);
    if (pdfDocument !== this.#pdfDocument) {
      return;
    }
    this.#results.set(signature.id, result);
    this.#render();
    this.#updateButtonState();
  }
  #updateButtonState() {
    const button = this.#appConfig.signaturePropertiesButton;
    button.classList.remove("state-loading", "state-verified", "state-warn", "state-error");
    if (this.#signatures.length === 0) {
      return;
    }
    if (this.#pendingVerify.size > 0) {
      button.classList.add("state-loading");
      return;
    }
    switch (this.#worst) {
      case "invalid":
      case "revoked":
      case "unknown":
        button.classList.add("state-error");
        break;
      case "expired":
      case "untrusted":
        button.classList.add("state-warn");
        break;
      default:
        button.classList.add("state-verified");
    }
  }
}

;// ./web/toolbar.js



class Toolbar {
  #colorPicker = null;
  #opts;
  constructor(options, eventBus, toolbarDensity = 0) {
    this.#opts = options;
    this.eventBus = eventBus;
    const buttons = [{
      element: options.previous,
      eventName: "previouspage"
    }, {
      element: options.next,
      eventName: "nextpage"
    }, {
      element: options.zoomIn,
      eventName: "zoomin"
    }, {
      element: options.zoomOut,
      eventName: "zoomout"
    }, {
      element: options.print,
      eventName: "print"
    }, {
      element: options.download,
      eventName: "download"
    }, {
      element: options.editorCommentButton,
      eventName: "switchannotationeditormode",
      eventDetails: {
        get mode() {
          const {
            classList
          } = options.editorCommentButton;
          return classList.contains("toggled") ? AnnotationEditorType.NONE : AnnotationEditorType.POPUP;
        }
      }
    }, {
      element: options.editorFreeTextButton,
      eventName: "switchannotationeditormode",
      eventDetails: {
        get mode() {
          const {
            classList
          } = options.editorFreeTextButton;
          return classList.contains("toggled") ? AnnotationEditorType.NONE : AnnotationEditorType.FREETEXT;
        }
      }
    }, {
      element: options.editorHighlightButton,
      eventName: "switchannotationeditormode",
      eventDetails: {
        get mode() {
          const {
            classList
          } = options.editorHighlightButton;
          return classList.contains("toggled") ? AnnotationEditorType.NONE : AnnotationEditorType.HIGHLIGHT;
        }
      }
    }, {
      element: options.editorInkButton,
      eventName: "switchannotationeditormode",
      eventDetails: {
        get mode() {
          const {
            classList
          } = options.editorInkButton;
          return classList.contains("toggled") ? AnnotationEditorType.NONE : AnnotationEditorType.INK;
        }
      }
    }, {
      element: options.editorStampButton,
      eventName: "switchannotationeditormode",
      eventDetails: {
        get mode() {
          const {
            classList
          } = options.editorStampButton;
          return classList.contains("toggled") ? AnnotationEditorType.NONE : AnnotationEditorType.STAMP;
        }
      },
      telemetry: {
        type: "editing",
        data: {
          action: "pdfjs.image.icon_click"
        }
      }
    }, {
      element: options.editorSignatureButton,
      eventName: "switchannotationeditormode",
      eventDetails: {
        get mode() {
          const {
            classList
          } = options.editorSignatureButton;
          return classList.contains("toggled") ? AnnotationEditorType.NONE : AnnotationEditorType.SIGNATURE;
        }
      }
    }];
    this.#bindListeners(buttons);
    this.#updateToolbarDensity({
      value: toolbarDensity
    });
    this.reset();
  }
  #updateToolbarDensity({
    value
  }) {
    let name = "normal";
    switch (value) {
      case 1:
        name = "compact";
        break;
      case 2:
        name = "touch";
        break;
    }
    document.documentElement.setAttribute("data-toolbar-density", name);
  }
  setPageNumber(pageNumber, pageLabel) {
    this.pageNumber = pageNumber;
    this.pageLabel = pageLabel;
    this.#updateUIState(false);
  }
  setPagesCount(pagesCount, hasPageLabels) {
    this.pagesCount = pagesCount;
    this.hasPageLabels = hasPageLabels;
    this.#updateUIState(true);
  }
  setPageScale(pageScaleValue, pageScale) {
    this.pageScaleValue = (pageScaleValue || pageScale).toString();
    this.pageScale = pageScale;
    this.#updateUIState(false);
  }
  reset() {
    this.#colorPicker = null;
    this.pageNumber = 0;
    this.pageLabel = null;
    this.hasPageLabels = false;
    this.pagesCount = 0;
    this.pageScaleValue = (/* inlined export .DEFAULT_SCALE_VALUE */"auto");
    this.pageScale = (/* inlined export .DEFAULT_SCALE */1);
    this.#updateUIState(true);
    this.updateLoadingIndicatorState();
    this.#editorModeChanged({
      mode: AnnotationEditorType.DISABLE
    });
  }
  #bindListeners(buttons) {
    const {
      eventBus
    } = this;
    const {
      editorHighlightColorPicker,
      editorHighlightButton,
      pageNumber,
      scaleSelect
    } = this.#opts;
    const self = this;
    for (const {
      element,
      eventName,
      eventDetails,
      telemetry
    } of buttons) {
      element.addEventListener("click", evt => {
        if (eventName !== null) {
          eventBus.dispatch(eventName, {
            source: this,
            ...eventDetails,
            isFromKeyboard: evt.detail === 0
          });
        }
        if (telemetry) {
          eventBus.dispatch("reporttelemetry", {
            source: this,
            details: telemetry
          });
        }
      });
    }
    pageNumber.addEventListener("click", function () {
      this.select();
    });
    pageNumber.addEventListener("change", function () {
      eventBus.dispatch("pagenumberchanged", {
        source: self,
        value: this.value
      });
    });
    eventBus.on("pagesedited", ({
      pagesMapper
    }) => {
      const pagesCount = pagesMapper.pagesNumber;
      if (pagesCount !== this.pagesCount) {
        this.setPagesCount(pagesCount, this.hasPageLabels);
      }
    }, internalOpt);
    scaleSelect.addEventListener("change", function () {
      if (this.value === "custom") {
        return;
      }
      eventBus.dispatch("scalechanged", {
        source: self,
        value: this.value
      });
    });
    scaleSelect.addEventListener("click", function ({
      target
    }) {
      if (this.value === self.pageScaleValue && target.tagName.toUpperCase() === "OPTION") {
        this.blur();
      }
    });
    scaleSelect.oncontextmenu = noContextMenu;
    eventBus.on("annotationeditormodechanged", this.#editorModeChanged.bind(this), internalOpt);
    eventBus.on("showannotationeditorui", ({
      mode
    }) => {
      switch (mode) {
        case AnnotationEditorType.HIGHLIGHT:
          editorHighlightButton.click();
          break;
      }
    }, internalOpt);
    eventBus.on("toolbardensity", this.#updateToolbarDensity.bind(this), internalOpt);
    if (editorHighlightColorPicker) {
      eventBus.on("annotationeditoruimanager", ({
        uiManager
      }) => {
        const cp = this.#colorPicker = new ColorPicker({
          uiManager
        });
        uiManager.setMainHighlightColorPicker(cp);
        editorHighlightColorPicker.append(cp.renderMainDropdown());
      }, internalOpt);
      eventBus.on("mainhighlightcolorpickerupdatecolor", ({
        value
      }) => {
        this.#colorPicker?.update(value);
      }, internalOpt);
    }
  }
  #editorModeChanged({
    mode
  }) {
    const {
      editorCommentButton,
      editorCommentParamsToolbar,
      editorFreeTextButton,
      editorFreeTextParamsToolbar,
      editorHighlightButton,
      editorHighlightParamsToolbar,
      editorInkButton,
      editorInkParamsToolbar,
      editorStampButton,
      editorStampParamsToolbar,
      editorSignatureButton,
      editorSignatureParamsToolbar
    } = this.#opts;
    toggleExpandedBtn(editorCommentButton, mode === AnnotationEditorType.POPUP, editorCommentParamsToolbar);
    toggleExpandedBtn(editorFreeTextButton, mode === AnnotationEditorType.FREETEXT, editorFreeTextParamsToolbar);
    toggleExpandedBtn(editorHighlightButton, mode === AnnotationEditorType.HIGHLIGHT, editorHighlightParamsToolbar);
    toggleExpandedBtn(editorInkButton, mode === AnnotationEditorType.INK, editorInkParamsToolbar);
    toggleExpandedBtn(editorStampButton, mode === AnnotationEditorType.STAMP, editorStampParamsToolbar);
    toggleExpandedBtn(editorSignatureButton, mode === AnnotationEditorType.SIGNATURE, editorSignatureParamsToolbar);
    editorCommentButton.disabled = editorFreeTextButton.disabled = editorHighlightButton.disabled = editorInkButton.disabled = editorStampButton.disabled = editorSignatureButton.disabled = mode === AnnotationEditorType.DISABLE;
  }
  #updateUIState(resetNumPages = false) {
    const {
      pageNumber,
      pagesCount,
      pageScaleValue,
      pageScale
    } = this;
    const opts = this.#opts;
    if (resetNumPages) {
      if (this.hasPageLabels) {
        opts.pageNumber.type = "text";
        opts.numPages.setAttribute("data-l10n-id", "pdfjs-page-of-pages");
      } else {
        opts.pageNumber.type = "number";
        opts.numPages.setAttribute("data-l10n-id", "pdfjs-of-pages");
        opts.numPages.setAttribute("data-l10n-args", JSON.stringify({
          pagesCount
        }));
      }
      opts.pageNumber.max = pagesCount;
    }
    if (this.hasPageLabels) {
      opts.pageNumber.value = this.pageLabel;
      opts.numPages.setAttribute("data-l10n-args", JSON.stringify({
        pageNumber,
        pagesCount
      }));
    } else {
      opts.pageNumber.value = pageNumber;
    }
    opts.previous.disabled = pageNumber <= 1;
    opts.next.disabled = pageNumber >= pagesCount;
    opts.zoomOut.disabled = pageScale <= (/* inlined export .MIN_SCALE */0.1);
    opts.zoomIn.disabled = pageScale >= (/* inlined export .MAX_SCALE */25);
    let predefinedValueFound = false;
    for (const option of opts.scaleSelect.options) {
      if (option.value !== pageScaleValue) {
        option.selected = false;
        continue;
      }
      option.selected = true;
      predefinedValueFound = true;
    }
    if (!predefinedValueFound) {
      opts.customScaleOption.selected = true;
      opts.customScaleOption.setAttribute("data-l10n-args", JSON.stringify({
        scale: Math.round(pageScale * 10000) / 100
      }));
    }
  }
  updateLoadingIndicatorState(loading = false) {
    const {
      pageNumber
    } = this.#opts;
    pageNumber.classList.toggle("loading", loading);
  }
}

;// ./web/view_history.js
const DEFAULT_VIEW_HISTORY_CACHE_SIZE = 20;
class ViewHistory {
  constructor(fingerprint, cacheSize = DEFAULT_VIEW_HISTORY_CACHE_SIZE) {
    this._initializedPromise = this._readFromStorage().then(databaseStr => {
      const database = JSON.parse(databaseStr || "{}");
      let index = -1;
      if (!Array.isArray(database.files)) {
        database.files = [];
      } else {
        while (database.files.length >= cacheSize) {
          database.files.shift();
        }
        index = database.files.findIndex(branch => branch.fingerprint === fingerprint);
      }
      if (index === -1) {
        index = database.files.push({
          fingerprint
        }) - 1;
      }
      this.file = database.files[index];
      this.database = database;
    });
  }
  async _writeToStorage() {
    const databaseStr = JSON.stringify(this.database);
    localStorage.setItem("pdfjs.history", databaseStr);
  }
  async _readFromStorage() {
    return localStorage.getItem("pdfjs.history");
  }
  async setMultiple(properties) {
    await this._initializedPromise;
    for (const name in properties) {
      this.file[name] = properties[name];
    }
    return this._writeToStorage();
  }
  async getMultiple(properties) {
    await this._initializedPromise;
    const values = Object.create(null);
    for (const name in properties) {
      const val = this.file[name];
      values[name] = val !== undefined ? val : properties[name];
    }
    return values;
  }
}

;// ./web/views_manager.js




const SIDEBAR_WIDTH_VAR = "--viewsManager-width";
const SIDEBAR_RESIZING_CLASS = "viewsManagerResizing";
const UI_NOTIFICATION_CLASS = "pdfSidebarNotification";
class ViewsManager extends Sidebar {
  static #l10nDescription = null;
  #hasAnimations = !window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  constructor({
    elements: {
      outerContainer,
      sidebarContainer,
      toggleButton,
      resizer,
      thumbnailButton,
      outlineButton,
      attachmentsButton,
      layersButton,
      thumbnailsView,
      outlinesView,
      attachmentsView,
      layersView,
      viewsManagerAddFile: {
        button: viewsManagerAddFileButton
      },
      viewsManagerCurrentOutlineButton,
      viewsManagerSelectorButton,
      viewsManagerSelectorOptions,
      viewsManagerHeaderLabel,
      viewsManagerStatus
    },
    eventBus,
    l10n,
    enableMerge = false,
    enableSplitMerge = false,
    globalAbortSignal
  }) {
    super({
      sidebar: sidebarContainer,
      resizer,
      toggleButton
    }, l10n.getDirection() === "ltr", false, globalAbortSignal);
    this.isOpen = false;
    this.active = SidebarView.THUMBS;
    this.isInitialViewSet = false;
    this.isInitialEventDispatched = false;
    this.onToggled = null;
    this.onUpdateThumbnails = null;
    this.outerContainer = outerContainer;
    this.sidebarContainer = sidebarContainer;
    this.toggleButton = toggleButton;
    this.resizer = resizer;
    this.thumbnailButton = thumbnailButton;
    this.outlineButton = outlineButton;
    this.attachmentsButton = attachmentsButton;
    this.layersButton = layersButton;
    this.thumbnailsView = thumbnailsView;
    this.outlinesView = outlinesView;
    this.attachmentsView = attachmentsView;
    this.layersView = layersView;
    this.viewsManagerAddFileButton = viewsManagerAddFileButton;
    this.viewsManagerCurrentOutlineButton = viewsManagerCurrentOutlineButton;
    this.viewsManagerHeaderLabel = viewsManagerHeaderLabel;
    this.viewsManagerStatus = viewsManagerStatus;
    this.eventBus = eventBus;
    if (!enableSplitMerge) {
      viewsManagerStatus.hidden = true;
    }
    this._enableSplitMerge = enableSplitMerge;
    this._enableMerge = enableMerge;
    if (!enableMerge) {
      viewsManagerAddFileButton.hidden = true;
    }
    this.menu = new Menu(viewsManagerSelectorOptions, viewsManagerSelectorButton, [thumbnailButton, outlineButton, attachmentsButton, layersButton]);
    ViewsManager.#l10nDescription ||= Object.freeze({
      pagesTitle: "pdfjs-views-manager-pages-title",
      outlinesTitle: "pdfjs-views-manager-outlines-title1",
      attachmentsTitle: "pdfjs-views-manager-attachments-title",
      layersTitle: "pdfjs-views-manager-layers-title1",
      notificationButton: "pdfjs-toggle-views-manager-notification-button",
      toggleButton: "pdfjs-toggle-views-manager-button1"
    });
    this.#addEventListeners();
  }
  reset() {
    this.isInitialViewSet = false;
    this.isInitialEventDispatched = false;
    this.#hideUINotification(true);
    this.switchView(SidebarView.THUMBS);
    this.outlineButton.disabled = this.attachmentsButton.disabled = this.layersButton.disabled = false;
    this.viewsManagerCurrentOutlineButton.disabled = true;
  }
  get visibleView() {
    return this.isOpen ? this.active : SidebarView.NONE;
  }
  setInitialView(view = SidebarView.NONE) {
    if (this.isInitialViewSet) {
      return;
    }
    this.isInitialViewSet = true;
    if (view === SidebarView.NONE || view === SidebarView.UNKNOWN) {
      this.#dispatchEvent();
      return;
    }
    this.switchView(view, true);
    if (!this.isInitialEventDispatched) {
      this.#dispatchEvent();
    }
  }
  switchView(view, forceOpen = false) {
    const isViewChanged = view !== this.active;
    let forceRendering = false;
    let titleL10nId = null;
    switch (view) {
      case SidebarView.NONE:
        if (this.isOpen) {
          this.close();
        }
        return;
      case SidebarView.THUMBS:
        titleL10nId = "pagesTitle";
        if (this.isOpen && isViewChanged) {
          forceRendering = true;
        }
        break;
      case SidebarView.OUTLINE:
        titleL10nId = "outlinesTitle";
        if (this.outlineButton.disabled) {
          return;
        }
        break;
      case SidebarView.ATTACHMENTS:
        titleL10nId = "attachmentsTitle";
        if (this.attachmentsButton.disabled) {
          return;
        }
        break;
      case SidebarView.LAYERS:
        titleL10nId = "layersTitle";
        if (this.layersButton.disabled) {
          return;
        }
        break;
      default:
        console.error(`PDFSidebar.switchView: "${view}" is not a valid view.`);
        return;
    }
    this.viewsManagerStatus.hidden = !this._enableSplitMerge || view !== SidebarView.THUMBS;
    this.viewsManagerAddFileButton.hidden = !this._enableMerge || view !== SidebarView.THUMBS;
    this.viewsManagerCurrentOutlineButton.hidden = view !== SidebarView.OUTLINE;
    this.viewsManagerHeaderLabel.setAttribute("data-l10n-id", ViewsManager.#l10nDescription[titleL10nId] || "");
    this.active = view;
    toggleSelectedBtn(this.thumbnailButton, view === SidebarView.THUMBS, this.thumbnailsView);
    toggleSelectedBtn(this.outlineButton, view === SidebarView.OUTLINE, this.outlinesView);
    toggleSelectedBtn(this.attachmentsButton, view === SidebarView.ATTACHMENTS, this.attachmentsView);
    toggleSelectedBtn(this.layersButton, view === SidebarView.LAYERS, this.layersView);
    if (forceOpen && !this.isOpen) {
      this.open();
      return;
    }
    if (forceRendering) {
      this.onUpdateThumbnails();
      this.onToggled();
    }
    if (isViewChanged) {
      this.#dispatchEvent();
    }
  }
  open() {
    if (this.isOpen) {
      return;
    }
    this.isOpen = true;
    this.onResizing(this.width);
    this._sidebar.hidden = false;
    toggleExpandedBtn(this.toggleButton, true);
    this.switchView(this.active);
    if (this.#hasAnimations) {
      queueMicrotask(() => {
        this.outerContainer.classList.add("viewsManagerMoving", "viewsManagerOpen");
      });
    } else {
      this.outerContainer.classList.add("viewsManagerOpen");
      this.eventBus.dispatch("resize", {
        source: this
      });
    }
    if (this.active === SidebarView.THUMBS) {
      this.onUpdateThumbnails();
    }
    this.onToggled();
    this.#dispatchEvent();
    this.#hideUINotification();
  }
  close(evt = null) {
    if (!this.isOpen) {
      return;
    }
    this.isOpen = false;
    this._sidebar.hidden = true;
    toggleExpandedBtn(this.toggleButton, false);
    this.outerContainer.classList.add("viewsManagerMoving");
    this.outerContainer.classList.remove("viewsManagerOpen");
    this.onToggled();
    this.#dispatchEvent();
    if (evt?.detail > 0) {
      this.toggleButton.blur();
    }
  }
  toggle(evt = null) {
    super.toggle();
    if (this.isOpen) {
      this.close(evt);
    } else {
      this.open();
    }
  }
  #dispatchEvent() {
    if (this.isInitialViewSet) {
      this.isInitialEventDispatched ||= true;
    }
    this.eventBus.dispatch("sidebarviewchanged", {
      source: this,
      view: this.visibleView
    });
  }
  #showUINotification() {
    this.toggleButton.setAttribute("data-l10n-id", ViewsManager.#l10nDescription.notificationButton);
    if (!this.isOpen) {
      this.toggleButton.classList.add(UI_NOTIFICATION_CLASS);
    }
  }
  #hideUINotification(reset = false) {
    if (this.isOpen || reset) {
      this.toggleButton.classList.remove(UI_NOTIFICATION_CLASS);
    }
    if (reset) {
      this.toggleButton.setAttribute("data-l10n-id", ViewsManager.#l10nDescription.toggleButton);
    }
  }
  #addEventListeners() {
    const {
      eventBus,
      outerContainer
    } = this;
    if (this.#hasAnimations) {
      this.sidebarContainer.addEventListener("transitionend", evt => {
        if (evt.target === this.sidebarContainer) {
          outerContainer.classList.remove("viewsManagerMoving");
          eventBus.dispatch("resize", {
            source: this
          });
        }
      });
    }
    this.viewsManagerHeaderLabel.addEventListener("dblclick", e => {
      if (this.active === SidebarView.OUTLINE) {
        eventBus.dispatch("toggleoutlinetree", {
          source: this
        });
        return;
      }
      if (this.active === SidebarView.LAYERS) {
        eventBus.dispatch("resetlayers", {
          source: this
        });
      }
    });
    this.thumbnailButton.addEventListener("click", () => {
      this.switchView(SidebarView.THUMBS);
    });
    this.outlineButton.addEventListener("click", () => {
      this.switchView(SidebarView.OUTLINE);
    });
    this.attachmentsButton.addEventListener("click", () => {
      this.switchView(SidebarView.ATTACHMENTS);
    });
    this.layersButton.addEventListener("click", () => {
      this.switchView(SidebarView.LAYERS);
    });
    this.viewsManagerCurrentOutlineButton.addEventListener("click", () => {
      eventBus.dispatch("currentoutlineitem", {
        source: this
      });
    });
    const onTreeLoaded = (count, button, view) => {
      button.disabled = !count;
      if (count) {
        this.#showUINotification();
      } else if (this.active === view) {
        this.switchView(SidebarView.THUMBS);
      }
    };
    eventBus.on("outlineloaded", evt => {
      onTreeLoaded(evt.outlineCount, this.outlineButton, SidebarView.OUTLINE);
      evt.currentOutlineItemPromise.then(enabled => {
        if (!this.isInitialViewSet) {
          return;
        }
        this.viewsManagerCurrentOutlineButton.disabled = !enabled;
      });
    }, internalOpt);
    eventBus.on("attachmentsloaded", evt => {
      onTreeLoaded(evt.attachmentsCount, this.attachmentsButton, SidebarView.ATTACHMENTS);
    }, internalOpt);
    eventBus.on("layersloaded", evt => {
      onTreeLoaded(evt.layersCount, this.layersButton, SidebarView.LAYERS);
    }, internalOpt);
    eventBus.on("presentationmodechanged", evt => {
      if (evt.state === PresentationModeState.NORMAL && this.visibleView === SidebarView.THUMBS) {
        this.onUpdateThumbnails();
      }
    }, internalOpt);
  }
  onStartResizing() {
    this.outerContainer.classList.add(SIDEBAR_RESIZING_CLASS);
  }
  onStopResizing() {
    this.eventBus.dispatch("resize", {
      source: this
    });
    this.outerContainer.classList.remove(SIDEBAR_RESIZING_CLASS);
  }
  onResizing(newWidth) {
    docStyle.setProperty(SIDEBAR_WIDTH_VAR, `${newWidth}px`);
  }
}

;// ./web/app.js







































const FORCE_PAGES_LOADED_TIMEOUT = 10000;
const ViewOnLoad = {
  UNKNOWN: -1,
  PREVIOUS: 0,
  INITIAL: 1
};
const PDFViewerApplication = {
  initialBookmark: document.location.hash.substring(1),
  _initializedCapability: {
    ...Promise.withResolvers(),
    settled: false
  },
  appConfig: null,
  pdfDocument: null,
  pdfLoadingTask: null,
  printService: null,
  pdfViewer: null,
  pdfThumbnailViewer: null,
  pdfRenderingQueue: null,
  pdfPresentationMode: null,
  pdfDocumentProperties: null,
  pdfLinkService: null,
  pdfTextExtractor: null,
  pdfHistory: null,
  viewsManager: null,
  pdfOutlineViewer: null,
  pdfAttachmentViewer: null,
  pdfLayerViewer: null,
  pdfCursorTools: null,
  pdfScriptingManager: null,
  store: null,
  downloadManager: null,
  overlayManager: null,
  preferences: new Preferences(),
  toolbar: null,
  secondaryToolbar: null,
  eventBus: null,
  l10n: null,
  annotationEditorParams: null,
  signaturePropertiesManager: null,
  imageAltTextSettings: null,
  isInitialViewSet: false,
  isViewerEmbedded: window.parent !== window,
  url: "",
  baseUrl: "",
  mlManager: null,
  _downloadUrl: "",
  _isMergedDocument: false,
  _eventBusAC: null,
  _windowAC: null,
  _globalAbortController: new AbortController(),
  documentInfo: null,
  metadata: null,
  _contentDispositionFilename: null,
  _contentLength: null,
  _saveInProgress: false,
  _wheelUnusedTicks: 0,
  _wheelUnusedFactor: 1,
  _touchManager: null,
  _touchUnusedTicks: 0,
  _touchUnusedFactor: 1,
  _PDFBug: null,
  _hasAnnotationEditors: false,
  _title: document.title,
  _printAnnotationStoragePromise: null,
  _isCtrlKeyDown: false,
  _caretBrowsing: null,
  _isScrolling: false,
  editorUndoBar: null,
  _printPermissionPromise: null,
  async initialize(appConfig) {
    this.appConfig = appConfig;
    try {
      await this.preferences.initializedPromise;
    } catch (ex) {
      console.error("initialize:", ex);
    }
    if (AppOptions.get("pdfBugEnabled")) {
      await this._parseHashParams();
    }
    let mode;
    switch (AppOptions.get("viewerCssTheme")) {
      case 1:
        mode = "light";
        break;
      case 2:
        mode = "dark";
        break;
    }
    if (mode) {
      docStyle.setProperty("color-scheme", mode);
    }
    this.l10n = await this.externalServices.createL10n();
    document.getElementsByTagName("html")[0].dir = this.l10n.getDirection();
    this.l10n.translate(appConfig.appContainer || document.documentElement);
    if (this.isViewerEmbedded && AppOptions.get("externalLinkTarget") === LinkTarget.NONE) {
      AppOptions.set("externalLinkTarget", LinkTarget.TOP);
    }
    await this._initializeViewerComponents();
    this.bindEvents();
    this.bindWindowEvents();
    this._initializedCapability.settled = true;
    this._initializedCapability.resolve();
  },
  async _parseHashParams() {
    const hash = document.location.hash.substring(1);
    if (!hash) {
      return;
    }
    const {
        mainContainer,
        viewerContainer
      } = this.appConfig,
      params = parseQueryString(hash);
    const loadPDFBug = async () => {
      if (this._PDFBug) {
        return;
      }
      const {
        PDFBug
      } = await import(
      /*webpackIgnore: true*/
      /*@vite-ignore*/
      AppOptions.get("debuggerSrc"));
      this._PDFBug = PDFBug;
    };
    if (params.get("disableworker") === "true") {
      try {
        GlobalWorkerOptions.workerSrc ||= AppOptions.get("workerSrc");
        await import(
        /*webpackIgnore: true*/
        /*@vite-ignore*/
        PDFWorker.workerSrc);
        AppOptions.set("workerPort", null);
      } catch (ex) {
        console.error("_parseHashParams:", ex);
      }
    }
    if (params.has("textlayer")) {
      switch (params.get("textlayer")) {
        case "off":
          AppOptions.set("textLayerMode", TextLayerMode.DISABLE);
          break;
        case "visible":
        case "shadow":
        case "hover":
          viewerContainer.classList.add(`textLayer-${params.get("textlayer")}`);
          try {
            await loadPDFBug();
            this._PDFBug.loadCSS();
          } catch (ex) {
            console.error("_parseHashParams:", ex);
          }
          break;
      }
    }
    if (params.has("pdfbug")) {
      const enabled = params.get("pdfbug").split(",");
      try {
        await loadPDFBug();
        this._PDFBug.init(mainContainer, enabled);
      } catch (ex) {
        console.error("_parseHashParams:", ex);
      }
      const debugOpts = {
        pdfBug: true,
        fontExtraProperties: true
      };
      if (globalThis.StepperManager?.enabled) {
        debugOpts.minDurationToUpdateCanvas = 0;
      }
      AppOptions.setAll(debugOpts);
    }
    if (params.has("locale")) {
      AppOptions.set("localeProperties", {
        lang: params.get("locale")
      });
    }
    const opts = {
      disableAutoFetch: x => x === "true",
      disableFontFace: x => x === "true",
      disableHistory: x => x === "true",
      disableRange: x => x === "true",
      disableStream: x => x === "true",
      verbosity: x => x | 0
    };
    for (const name in opts) {
      const check = opts[name],
        key = name.toLowerCase();
      if (params.has(key)) {
        AppOptions.set(name, check(params.get(key)));
      }
    }
  },
  async _initializeViewerComponents() {
    const {
      appConfig,
      externalServices,
      l10n,
      mlManager
    } = this;
    const abortSignal = this._globalAbortController.signal;
    const eventBus = new EventBus();
    this.eventBus = AppOptions.eventBus = eventBus;
    mlManager?.setEventBus(eventBus, abortSignal);
    const overlayManager = this.overlayManager = new OverlayManager();
    const renderingQueue = this.pdfRenderingQueue = new PDFRenderingQueue();
    renderingQueue.onIdle = this._cleanup.bind(this);
    const linkService = this.pdfLinkService = new PDFLinkService({
      eventBus,
      externalLinkTarget: AppOptions.get("externalLinkTarget"),
      externalLinkRel: AppOptions.get("externalLinkRel"),
      ignoreDestinationZoom: AppOptions.get("ignoreDestinationZoom")
    });
    const supportsDownloading = AppOptions.get("supportsDownloading");
    const downloadManager = this.downloadManager = supportsDownloading ? new DownloadManager() : null;
    if (appConfig.secondaryToolbar?.downloadButton) {
      appConfig.secondaryToolbar.downloadButton.hidden = !supportsDownloading;
    }
    if (appConfig.toolbar?.download) {
      appConfig.toolbar.download.hidden = !supportsDownloading;
    }
    const findController = this.findController = new PDFFindController({
      linkService,
      eventBus,
      updateMatchesCountOnProgress: true
    });
    const pdfScriptingManager = this.pdfScriptingManager = new PDFScriptingManager({
      eventBus,
      externalServices,
      docProperties: this._scriptingDocProperties.bind(this)
    });
    const container = appConfig.mainContainer,
      viewer = appConfig.viewerContainer;
    const annotationEditorMode = AppOptions.get("annotationEditorMode");
    const hasForcedColors = AppOptions.get("forcePageColors") || window.matchMedia("(forced-colors: active)").matches;
    const pageColors = hasForcedColors ? {
      background: AppOptions.get("pageColorsBackground"),
      foreground: AppOptions.get("pageColorsForeground")
    } : null;
    const enableMerge = AppOptions.get("enableMerge");
    const enableSplitMerge = AppOptions.get("enableSplitMerge");
    let altTextManager;
    if (AppOptions.get("enableUpdatedAddImage")) {
      altTextManager = appConfig.newAltTextDialog ? new NewAltTextManager(appConfig.newAltTextDialog, overlayManager, eventBus) : null;
    } else {
      altTextManager = appConfig.altTextDialog ? new AltTextManager(appConfig.altTextDialog, container, overlayManager, eventBus) : null;
    }
    if (appConfig.editorUndoBar) {
      this.editorUndoBar = new EditorUndoBar(appConfig.editorUndoBar, eventBus);
    }
    let signatureManager = null;
    if (AppOptions.get("enableSignatureEditor")) {
      if (appConfig.addSignatureDialog) {
        signatureManager = new SignatureManager(appConfig.addSignatureDialog, appConfig.editSignatureDialog, appConfig.annotationEditorParams?.editorSignatureAddSignature || null, overlayManager, l10n, externalServices.createSignatureStorage(eventBus, abortSignal), eventBus);
      }
    }
    const commentManager = AppOptions.get("enableComment") && appConfig.editCommentDialog ? new CommentManager(appConfig.editCommentDialog, {
      learnMoreUrl: AppOptions.get("commentLearnMoreUrl"),
      sidebar: appConfig.annotationEditorParams?.editorCommentsSidebar || null,
      sidebarResizer: appConfig.annotationEditorParams?.editorCommentsSidebarResizer || null,
      commentsList: appConfig.annotationEditorParams?.editorCommentsSidebarList || null,
      commentCount: appConfig.annotationEditorParams?.editorCommentsSidebarCount || null,
      sidebarTitle: appConfig.annotationEditorParams?.editorCommentsSidebarTitle || null,
      closeButton: appConfig.annotationEditorParams?.editorCommentsSidebarCloseButton || null,
      commentToolbarButton: appConfig.toolbar?.editorCommentButton || null
    }, eventBus, linkService, overlayManager, l10n.getDirection() === "ltr", hasForcedColors, abortSignal) : null;
    const maxCanvasPixels = AppOptions.get("maxCanvasPixels"),
      maxCanvasDim = AppOptions.get("maxCanvasDim"),
      capCanvasAreaFactor = AppOptions.get("capCanvasAreaFactor");
    const pdfViewer = this.pdfViewer = new PDFViewer({
      container,
      viewer,
      viewerAlert: appConfig.viewerAlert,
      eventBus,
      renderingQueue,
      linkService,
      downloadManager,
      altTextManager,
      commentManager,
      signatureManager,
      editorUndoBar: this.editorUndoBar,
      findController,
      scriptingManager: AppOptions.get("enableScripting") && pdfScriptingManager,
      l10n,
      textLayerMode: AppOptions.get("textLayerMode"),
      annotationMode: AppOptions.get("annotationMode"),
      annotationEditorMode,
      annotationEditorHighlightColors: AppOptions.get("highlightEditorColors"),
      enableHighlightFloatingButton: AppOptions.get("enableHighlightFloatingButton"),
      enableUpdatedAddImage: AppOptions.get("enableUpdatedAddImage"),
      enableNewAltTextWhenAddingImage: AppOptions.get("enableNewAltTextWhenAddingImage"),
      imageResourcesPath: AppOptions.get("imageResourcesPath"),
      enablePrintAutoRotate: AppOptions.get("enablePrintAutoRotate"),
      maxCanvasPixels,
      maxCanvasDim,
      capCanvasAreaFactor,
      enableDetailCanvas: AppOptions.get("enableDetailCanvas"),
      enablePermissions: AppOptions.get("enablePermissions"),
      enableOptimizedPartialRendering: AppOptions.get("enableOptimizedPartialRendering"),
      enableSelectionRendering: AppOptions.get("enableSelectionRendering"),
      imagesRightClickMinSize: AppOptions.get("imagesRightClickMinSize"),
      pageColors,
      mlManager,
      abortSignal,
      supportsPinchToZoom: this.supportsPinchToZoom,
      enableAutoLinking: AppOptions.get("enableAutoLinking"),
      minDurationToUpdateCanvas: AppOptions.get("minDurationToUpdateCanvas")
    });
    renderingQueue.setViewer(pdfViewer);
    linkService.setViewer(pdfViewer);
    pdfScriptingManager.setViewer(pdfViewer);
    if (appConfig.viewsManager?.thumbnailsView) {
      const {
        viewsManager
      } = appConfig;
      this.pdfThumbnailViewer = new PDFThumbnailViewer({
        container: viewsManager.thumbnailsView,
        eventBus,
        renderingQueue,
        linkService,
        l10n,
        maxCanvasPixels,
        maxCanvasDim,
        pageColors,
        abortSignal,
        enableSplitMerge,
        enableMerge,
        enableNewBadge: AppOptions.get("enableNewBadge"),
        statusBar: viewsManager.viewsManagerStatusBar,
        undoBar: viewsManager.viewsManagerUndoBar,
        manageMenu: viewsManager.manageMenu,
        waitingBar: viewsManager.viewsManagerWaitingBar,
        addFileComponent: viewsManager.viewsManagerAddFile
      });
      renderingQueue.setThumbnailViewer(this.pdfThumbnailViewer);
    }
    if (!this.isViewerEmbedded && !AppOptions.get("disableHistory")) {
      this.pdfHistory = new PDFHistory({
        linkService,
        eventBus
      });
      linkService.setHistory(this.pdfHistory);
    }
    if (!this.supportsIntegratedFind && appConfig.findBar) {
      this.findBar = new PDFFindBar(appConfig.findBar, appConfig.principalContainer, eventBus);
    }
    if (appConfig.annotationEditorParams) {
      if (annotationEditorMode !== AnnotationEditorType.DISABLE) {
        const editorSignatureButton = appConfig.toolbar?.editorSignatureButton;
        if (editorSignatureButton && AppOptions.get("enableSignatureEditor")) {
          editorSignatureButton.parentElement.hidden = false;
        }
        const editorCommentButton = appConfig.toolbar?.editorCommentButton;
        if (editorCommentButton && AppOptions.get("enableComment")) {
          editorCommentButton.parentElement.hidden = false;
        }
        this.annotationEditorParams = new AnnotationEditorParams(appConfig.annotationEditorParams, eventBus);
      } else {
        for (const id of ["editorModeButtons", "editorModeSeparator"]) {
          document.getElementById(id)?.classList.add("hidden");
        }
      }
    }
    if (mlManager && appConfig.secondaryToolbar?.imageAltTextSettingsButton) {
      this.imageAltTextSettings = new ImageAltTextSettings(appConfig.altTextSettingsDialog, overlayManager, eventBus, mlManager);
    }
    if (appConfig.documentProperties) {
      this.pdfDocumentProperties = new PDFDocumentProperties(appConfig.documentProperties, overlayManager, eventBus, l10n, () => this._docFilename, () => this._docTitle);
    }
    if (appConfig.secondaryToolbar?.cursorHandToolButton) {
      this.pdfCursorTools = new PDFCursorTools({
        container,
        eventBus,
        cursorToolOnLoad: AppOptions.get("cursorToolOnLoad")
      });
    }
    if (appConfig.toolbar) {
      this.toolbar = new Toolbar(appConfig.toolbar, eventBus, AppOptions.get("toolbarDensity"));
    }
    if (appConfig.secondaryToolbar) {
      if (AppOptions.get("enableAltText") && this.imageAltTextSettings) {
        appConfig.secondaryToolbar.imageAltTextSettingsButton?.classList.remove("hidden");
        appConfig.secondaryToolbar.imageAltTextSettingsSeparator?.classList.remove("hidden");
      }
      this.secondaryToolbar = new SecondaryToolbar(appConfig.secondaryToolbar, eventBus);
    }
    if (this.supportsFullscreen && appConfig.secondaryToolbar?.presentationModeButton) {
      this.pdfPresentationMode = new PDFPresentationMode({
        container,
        pdfViewer,
        eventBus
      });
    }
    if (appConfig.passwordOverlay) {
      this.passwordPrompt = new PasswordPrompt(appConfig.passwordOverlay, overlayManager, this.isViewerEmbedded);
    }
    if (appConfig.viewsManager?.outlinesView) {
      this.pdfOutlineViewer = new PDFOutlineViewer({
        container: appConfig.viewsManager.outlinesView,
        eventBus,
        l10n,
        linkService,
        downloadManager
      });
    }
    if (appConfig.viewsManager?.attachmentsView) {
      this.pdfAttachmentViewer = new PDFAttachmentViewer({
        container: appConfig.viewsManager.attachmentsView,
        eventBus,
        l10n,
        downloadManager,
        linkService
      });
    }
    if (appConfig.viewsManager?.layersView) {
      this.pdfLayerViewer = new PDFLayerViewer({
        container: appConfig.viewsManager.layersView,
        eventBus,
        l10n
      });
    }
    if (appConfig.viewsManager) {
      this.viewsManager = new ViewsManager({
        elements: appConfig.viewsManager,
        eventBus,
        l10n,
        enableMerge,
        enableSplitMerge,
        globalAbortSignal: abortSignal
      });
      this.viewsManager.onToggled = this.forceRendering.bind(this);
      this.viewsManager.onUpdateThumbnails = () => {
        for (const pageView of pdfViewer.getCachedPageViews()) {
          if (pageView.renderingState === RenderingStates.FINISHED) {
            this.pdfThumbnailViewer.getThumbnail(pageView.id - 1)?.setImage(pageView);
          }
        }
        this.pdfThumbnailViewer.scrollThumbnailIntoView(pdfViewer.currentPageNumber);
      };
    }
  },
  async run(config) {
    await this.initialize(config);
    const {
      appConfig,
      eventBus
    } = this;
    let file;
    const queryString = document.location.search.substring(1);
    const params = parseQueryString(queryString);
    file = params.get("file") ?? AppOptions.get("defaultUrl");
    file = URL.parse(file)?.href ?? file.replaceAll("#", "%23");
    validateFileURL(file);
    const fileInput = this._openFileInput = document.createElement("input");
    fileInput.id = "fileInput";
    fileInput.hidden = true;
    fileInput.type = "file";
    fileInput.value = null;
    document.body.append(fileInput);
    fileInput.addEventListener("change", function (evt) {
      const {
        files
      } = evt.target;
      if (!files?.length) {
        return;
      }
      eventBus.dispatch("fileinputchange", {
        source: this,
        fileInput: evt.target
      });
    });
    appConfig.mainContainer.addEventListener("dragover", function (evt) {
      for (const item of evt.dataTransfer.items) {
        if (item.type === "application/pdf") {
          evt.dataTransfer.dropEffect = evt.dataTransfer.effectAllowed === "copy" ? "copy" : "move";
          stopEvent(evt);
          return;
        }
      }
    });
    appConfig.mainContainer.addEventListener("drop", function (evt) {
      if (evt.dataTransfer.files?.[0].type !== "application/pdf") {
        return;
      }
      stopEvent(evt);
      eventBus.dispatch("fileinputchange", {
        source: this,
        fileInput: evt.dataTransfer
      });
    });
    if (!AppOptions.get("supportsDocumentFonts")) {
      AppOptions.set("disableFontFace", true);
      this.l10n.get("pdfjs-web-fonts-disabled").then(msg => {
        console.warn(msg);
      });
    }
    const togglePrintingButtons = visible => {
      appConfig.toolbar?.print?.classList.toggle("hidden", !visible);
      appConfig.secondaryToolbar?.printButton.classList.toggle("hidden", !visible);
    };
    if (!this.supportsPrinting) {
      togglePrintingButtons(false);
    } else {
      eventBus.on("printingallowed", ({
        isAllowed
      }) => togglePrintingButtons(isAllowed), internalOpt);
    }
    if (!this.supportsFullscreen) {
      appConfig.secondaryToolbar?.presentationModeButton.classList.add("hidden");
    }
    if (this.supportsIntegratedFind) {
      appConfig.findBar?.toggleButton?.classList.add("hidden");
    }
    if (file) {
      this.open({
        url: file
      });
    } else {
      this._hideViewBookmark();
    }
  },
  get externalServices() {
    return shadow(this, "externalServices", new ExternalServices());
  },
  get initialized() {
    return this._initializedCapability.settled;
  },
  get initializedPromise() {
    return this._initializedCapability.promise;
  },
  updateZoom(steps, scaleFactor, origin, pan = null) {
    if (this.pdfViewer.isInPresentationMode) {
      return;
    }
    this.pdfViewer.updateScale({
      drawingDelay: AppOptions.get("defaultZoomDelay"),
      steps,
      scaleFactor,
      origin,
      pan
    });
  },
  zoomIn() {
    this.updateZoom(1);
  },
  zoomOut() {
    this.updateZoom(-1);
  },
  zoomReset() {
    if (this.pdfViewer.isInPresentationMode) {
      return;
    }
    this.pdfViewer.currentScaleValue = (/* inlined export .DEFAULT_SCALE_VALUE */"auto");
  },
  touchPinchCallback(origin, prevDistance, distance, panX, panY) {
    const pan = [panX, panY];
    if (this.supportsPinchToZoom) {
      const newScaleFactor = this._accumulateFactor(this.pdfViewer.currentScale, distance / prevDistance, "_touchUnusedFactor");
      this.updateZoom(null, newScaleFactor, origin, pan);
    } else {
      const PIXELS_PER_LINE_SCALE = 30;
      const ticks = this._accumulateTicks((distance - prevDistance) / PIXELS_PER_LINE_SCALE, "_touchUnusedTicks");
      this.updateZoom(ticks, null, origin, pan);
    }
  },
  touchPanCallback(dx, dy) {
    const {
      pdfViewer
    } = this;
    if (!this.pdfDocument || pdfViewer.isInPresentationMode) {
      return;
    }
    pdfViewer.panBy(dx, dy);
  },
  touchPinchEndCallback() {
    this._touchUnusedTicks = 0;
    this._touchUnusedFactor = 1;
  },
  get pagesCount() {
    return this.pdfDocument ? this.pdfDocument.numPages : 0;
  },
  get page() {
    return this.pdfViewer.currentPageNumber;
  },
  set page(val) {
    this.pdfViewer.currentPageNumber = val;
  },
  get supportsPrinting() {
    return shadow(this, "supportsPrinting", AppOptions.get("supportsPrinting") && PDFPrintServiceFactory.supportsPrinting);
  },
  get supportsFullscreen() {
    return shadow(this, "supportsFullscreen", document.fullscreenEnabled);
  },
  get supportsPinchToZoom() {
    return shadow(this, "supportsPinchToZoom", AppOptions.get("supportsPinchToZoom"));
  },
  get supportsIntegratedFind() {
    return shadow(this, "supportsIntegratedFind", AppOptions.get("supportsIntegratedFind"));
  },
  get loadingBar() {
    const barElement = document.getElementById("loadingBar");
    const bar = barElement ? new ProgressBar(barElement) : null;
    return shadow(this, "loadingBar", bar);
  },
  get supportsMouseWheelZoomCtrlKey() {
    return shadow(this, "supportsMouseWheelZoomCtrlKey", AppOptions.get("supportsMouseWheelZoomCtrlKey"));
  },
  get supportsMouseWheelZoomMetaKey() {
    return shadow(this, "supportsMouseWheelZoomMetaKey", AppOptions.get("supportsMouseWheelZoomMetaKey"));
  },
  get supportsCaretBrowsingMode() {
    return AppOptions.get("supportsCaretBrowsingMode");
  },
  moveCaret(isUp, select) {
    this._caretBrowsing ||= new CaretBrowsingMode(this._globalAbortController.signal, this.appConfig.mainContainer, this.appConfig.viewerContainer, this.appConfig.toolbar?.container);
    this._caretBrowsing.moveCaret(isUp, select);
  },
  setTitleUsingUrl(url = "", downloadUrl = null) {
    this.url = url;
    this.baseUrl = updateUrlHash(url, "", true);
    if (downloadUrl) {
      this._downloadUrl = downloadUrl === url ? this.baseUrl : updateUrlHash(downloadUrl, "", true);
    }
    if (isDataScheme(url)) {
      this._hideViewBookmark();
    }
    let title = getPdfFilenameFromUrl(url, "");
    if (!title) {
      try {
        title = decodeURIComponent(getFilenameFromUrl(url));
      } catch {}
    }
    this.setTitle(title || url);
  },
  setTitle(title = this._title) {
    this._title = title;
    if (this.isViewerEmbedded) {
      return;
    }
    const hasChangesIndicator = this._hasChanges() && !this.pdfRenderingQueue.printing;
    document.title = `${hasChangesIndicator ? "* " : ""}${title}`;
  },
  get _docFilename() {
    return this._contentDispositionFilename || getPdfFilenameFromUrl(this.url);
  },
  get _docTitle() {
    const {
      documentInfo,
      metadata
    } = this;
    const title = metadata?.get("dc:title");
    if (title) {
      if (title !== "Untitled" && !/[\uFFF0-\uFFFF]/.test(title)) {
        return title;
      }
    }
    return documentInfo.Title;
  },
  _hideViewBookmark() {
    const {
      secondaryToolbar
    } = this.appConfig;
    secondaryToolbar?.viewBookmarkButton.classList.add("hidden");
    if (secondaryToolbar?.presentationModeButton.classList.contains("hidden")) {
      document.getElementById("viewBookmarkSeparator")?.classList.add("hidden");
    }
  },
  async close() {
    this._unblockDocumentLoadEvent();
    this._hideViewBookmark();
    if (!this.pdfLoadingTask) {
      return;
    }
    if (this._hasChanges() && this._annotationStorageModified) {
      try {
        await this.downloadOrSave();
      } catch {}
    }
    const promises = [];
    promises.push(this.pdfLoadingTask.destroy());
    this.pdfLoadingTask = null;
    if (this.pdfDocument) {
      this.pdfDocument = null;
      this.pdfThumbnailViewer?.setDocument(null);
      this.pdfViewer.setDocument(null);
      this.pdfLinkService.setDocument(null);
      this.pdfDocumentProperties?.setDocument(null);
      this.signaturePropertiesManager?.setDocument(null);
    }
    this.pdfLinkService.externalLinkEnabled = true;
    this.store = null;
    this.isInitialViewSet = false;
    this.url = "";
    this.baseUrl = "";
    this._downloadUrl = "";
    this._isMergedDocument = false;
    this.documentInfo = null;
    this.metadata = null;
    this._contentDispositionFilename = null;
    this._contentLength = null;
    this._saveInProgress = false;
    this._hasAnnotationEditors = false;
    promises.push(this.pdfScriptingManager.destroyPromise, this.passwordPrompt.close());
    this.setTitle();
    this.viewsManager?.reset();
    this.pdfOutlineViewer?.reset();
    this.pdfAttachmentViewer?.reset();
    this.pdfLayerViewer?.reset();
    this.pdfHistory?.reset();
    this.findBar?.reset();
    this.toolbar?.reset();
    this.secondaryToolbar?.reset();
    this._PDFBug?.cleanup();
    await Promise.all(promises);
  },
  async open(args) {
    if (this.pdfLoadingTask) {
      await this.close();
    }
    const workerParams = AppOptions.getAll(OptionKind.WORKER);
    Object.assign(GlobalWorkerOptions, workerParams);
    if (args.data && isPdfFile(args.filename)) {
      this._contentDispositionFilename = args.filename;
    } else if (args.url) {
      this.setTitleUsingUrl(args.originalUrl || args.url, args.url);
    }
    const apiParams = AppOptions.getAll(OptionKind.API);
    const loadingTask = getDocument({
      ...apiParams,
      ...args
    });
    this.pdfLoadingTask = loadingTask;
    loadingTask.onPassword = (updateCallback, reason) => {
      if (this.isViewerEmbedded) {
        this._unblockDocumentLoadEvent();
      }
      this.pdfLinkService.externalLinkEnabled = false;
      this.passwordPrompt.setUpdateCallback(updateCallback, reason);
      this.passwordPrompt.open();
    };
    loadingTask.onProgress = evt => this.progress(evt.percent);
    return loadingTask.promise.then(pdfDocument => {
      this.load(pdfDocument);
    }, reason => {
      if (loadingTask !== this.pdfLoadingTask) {
        return undefined;
      }
      if (this.loadingBar) {
        this.loadingBar.percent ||= 0;
      }
      let key = "pdfjs-loading-error";
      if (reason instanceof InvalidPDFException) {
        key = "pdfjs-invalid-file-error";
      } else if (reason instanceof ResponseException) {
        key = reason.missing ? "pdfjs-missing-file-error" : "pdfjs-unexpected-response-error";
      }
      return this._documentError(key, {
        message: reason.message
      }).then(() => {
        throw reason;
      });
    });
  },
  async download() {
    if (!this.downloadManager) {
      return;
    }
    let data;
    try {
      data = await (this.pdfDocument ? this.pdfDocument.getData() : this.pdfLoadingTask.getData());
    } catch {}
    this.downloadManager.download(data, this._downloadUrl, this._docFilename, this._isMergedDocument);
  },
  async save() {
    if (!this.downloadManager) {
      return;
    }
    if (this._saveInProgress) {
      return;
    }
    this._saveInProgress = true;
    const {
      pdfDocument
    } = this;
    try {
      await this.pdfScriptingManager.dispatchWillSave();
      const data = await pdfDocument.saveDocument(this.externalServices.printToPDF);
      this.downloadManager.download(data, this._downloadUrl, this._docFilename, true);
    } catch (reason) {
      console.error(`Error when saving the document:`, reason);
      if (pdfDocument === this.pdfDocument) {
        await this.download();
      }
    } finally {
      try {
        if (pdfDocument === this.pdfDocument) {
          await this.pdfScriptingManager.dispatchDidSave();
        }
      } finally {
        this._saveInProgress = false;
      }
    }
    const editorStats = this.pdfDocument?.annotationStorage.editorStats;
    if (editorStats) {
      this.externalServices.reportTelemetry({
        type: "editing",
        data: {
          type: "save",
          stats: editorStats
        }
      });
    }
  },
  async downloadOrSave() {
    if (!this.downloadManager) {
      return;
    }
    this.pdfViewer._layerProperties.annotationEditorUIManager?.endCurrentEditing();
    const {
      classList
    } = this.appConfig.appContainer;
    classList.add("wait");
    try {
      if (this.pdfThumbnailViewer?.hasStructuralChanges()) {
        this.externalServices.reportTelemetry({
          type: "pageOrganization",
          data: {
            action: "save"
          }
        });
        await this.onSavePages({
          data: this.pdfThumbnailViewer.getStructuralChanges()
        });
      } else {
        await (this.pdfDocument?.annotationStorage.size > 0 ? this.save() : this.download());
      }
      delete this._mergedDocumentNeedsSaving;
    } finally {
      this.setTitle();
      classList.remove("wait");
    }
  },
  async _documentError(key, moreInfo = null) {
    this._unblockDocumentLoadEvent();
    const message = await this._otherError(key || "pdfjs-loading-error", moreInfo);
    this.eventBus.dispatch("documenterror", {
      source: this,
      message,
      reason: moreInfo?.message ?? null
    });
  },
  async _otherError(key, moreInfo = null) {
    const message = await this.l10n.get(key);
    const moreInfoText = [`PDF.js v${version || "?"} (build: ${build || "?"})`];
    if (moreInfo) {
      moreInfoText.push(`Message: ${moreInfo.message}`);
      if (moreInfo.stack) {
        moreInfoText.push(`Stack: ${moreInfo.stack}`);
      } else {
        if (moreInfo.filename) {
          moreInfoText.push(`File: ${moreInfo.filename}`);
        }
        if (moreInfo.lineNumber) {
          moreInfoText.push(`Line: ${moreInfo.lineNumber}`);
        }
      }
    }
    console.error(`${message}\n\n${moreInfoText.join("\n")}`);
    return message;
  },
  progress(percent) {
    if (!this.loadingBar || percent <= this.loadingBar.percent) {
      return;
    }
    this.loadingBar.percent = percent;
    if (this.pdfDocument?.loadingParams.disableAutoFetch ?? AppOptions.get("disableAutoFetch")) {
      this.loadingBar.setDisableAutoFetch();
    }
  },
  load(pdfDocument) {
    this.pdfDocument = pdfDocument;
    this._printPermissionPromise = new Promise(resolve => {
      this.eventBus.on("printingallowed", ({
        isAllowed
      }) => {
        resolve(isAllowed);
      }, {
        once: true,
        ...internalOpt
      });
    });
    pdfDocument.getDownloadInfo().then(({
      length
    }) => {
      this._contentLength = length;
      this.loadingBar?.hide();
      firstPagePromise.then(() => {
        this.eventBus.dispatch("documentloaded", {
          source: this
        });
      });
    });
    const pageLayoutPromise = pdfDocument.getPageLayout().catch(() => {});
    const pageModePromise = pdfDocument.getPageMode().catch(() => {});
    const openActionPromise = pdfDocument.getOpenAction().catch(() => {});
    this.toolbar?.setPagesCount(pdfDocument.numPages, false);
    this.secondaryToolbar?.setPagesCount(pdfDocument.numPages);
    this.pdfLinkService.setDocument(pdfDocument);
    this.pdfDocumentProperties?.setDocument(pdfDocument);
    const pdfViewer = this.pdfViewer;
    pdfViewer.setDocument(pdfDocument);
    const {
      firstPagePromise,
      onePageRendered,
      pagesPromise
    } = pdfViewer;
    this.pdfThumbnailViewer?.setDocument(pdfDocument);
    const storedPromise = (this.store = new ViewHistory(pdfDocument.fingerprints[0])).getMultiple({
      page: null,
      zoom: (/* inlined export .DEFAULT_SCALE_VALUE */"auto"),
      scrollLeft: "0",
      scrollTop: "0",
      rotation: null,
      sidebarView: SidebarView.UNKNOWN,
      scrollMode: ScrollMode.UNKNOWN,
      spreadMode: SpreadMode.UNKNOWN
    }).catch(() => {});
    firstPagePromise.then(pdfPage => {
      this.loadingBar?.setWidth(this.appConfig.viewerContainer);
      this._initializeAnnotationStorageCallbacks(pdfDocument);
      Promise.all([animationStarted, storedPromise, pageLayoutPromise, pageModePromise, openActionPromise]).then(async ([timeStamp, stored, pageLayout, pageMode, openAction]) => {
        const viewOnLoad = AppOptions.get("viewOnLoad");
        this._initializePdfHistory({
          fingerprint: pdfDocument.fingerprints[0],
          viewOnLoad,
          initialDest: openAction?.get("dest")
        });
        const initialBookmark = this.initialBookmark;
        const zoom = AppOptions.get("defaultZoomValue");
        let hash = zoom ? `zoom=${zoom}` : null;
        let rotation = null;
        let sidebarView = AppOptions.get("sidebarViewOnLoad");
        let scrollMode = AppOptions.get("scrollModeOnLoad");
        let spreadMode = AppOptions.get("spreadModeOnLoad");
        if (stored?.page && viewOnLoad !== ViewOnLoad.INITIAL) {
          hash = `page=${stored.page}&zoom=${zoom || stored.zoom},` + `${stored.scrollLeft},${stored.scrollTop}`;
          rotation = parseInt(stored.rotation, 10);
          if (sidebarView === SidebarView.UNKNOWN) {
            sidebarView = stored.sidebarView | 0;
          }
          if (scrollMode === ScrollMode.UNKNOWN) {
            scrollMode = stored.scrollMode | 0;
          }
          if (spreadMode === SpreadMode.UNKNOWN) {
            spreadMode = stored.spreadMode | 0;
          }
        }
        if (pageMode && sidebarView === SidebarView.UNKNOWN) {
          sidebarView = apiPageModeToSidebarView(pageMode);
        }
        if (pageLayout && scrollMode === ScrollMode.UNKNOWN && spreadMode === SpreadMode.UNKNOWN) {
          const modes = apiPageLayoutToViewerModes(pageLayout);
          spreadMode = modes.spreadMode;
        }
        this.setInitialView(hash, {
          rotation,
          sidebarView,
          scrollMode,
          spreadMode
        });
        this.eventBus.dispatch("documentinit", {
          source: this
        });
        await Promise.race([pagesPromise, new Promise(resolve => {
          setTimeout(resolve, FORCE_PAGES_LOADED_TIMEOUT);
        })]);
        if (!initialBookmark && !hash) {
          return;
        }
        if (pdfViewer.hasEqualPageSizes) {
          return;
        }
        this.initialBookmark = initialBookmark;
        pdfViewer.currentScaleValue = pdfViewer.currentScaleValue;
        this.setInitialView(hash);
      }).catch(() => {
        this.setInitialView();
      }).then(function () {
        pdfViewer.update();
      });
    });
    pagesPromise.then(() => {
      this._unblockDocumentLoadEvent();
      this._initializeAutoPrint(pdfDocument, openActionPromise);
    }, reason => {
      this._documentError("pdfjs-loading-error", {
        message: reason.message
      });
    });
    onePageRendered.then(data => {
      this.externalServices.reportTelemetry({
        type: "pageInfo",
        timestamp: data.timestamp
      });
      if (this.pdfOutlineViewer) {
        pdfDocument.getOutline().then(outline => {
          if (pdfDocument !== this.pdfDocument) {
            return;
          }
          this.pdfOutlineViewer.render({
            outline,
            pdfDocument
          });
        }, reason => {
          if (pdfDocument !== this.pdfDocument) {
            return;
          }
          console.error("getOutline", reason);
          this.pdfOutlineViewer.render({
            outline: null,
            pdfDocument
          });
        });
      }
      if (this.pdfAttachmentViewer) {
        pdfDocument.getAttachments().then(attachments => {
          if (pdfDocument !== this.pdfDocument) {
            return;
          }
          this.pdfAttachmentViewer.render({
            attachments
          });
        }, reason => {
          if (pdfDocument !== this.pdfDocument) {
            return;
          }
          console.error("getAttachments", reason);
          this.pdfAttachmentViewer.render({
            attachments: null
          });
        });
      }
      if (this.pdfLayerViewer) {
        pdfViewer.optionalContentConfigPromise.then(optionalContentConfig => {
          if (pdfDocument !== this.pdfDocument) {
            return;
          }
          this.pdfLayerViewer.render({
            optionalContentConfig,
            pdfDocument
          });
        });
      }
    });
    this._initializePageLabels(pdfDocument);
    this._initializeMetadata(pdfDocument);
  },
  async _scriptingDocProperties(pdfDocument) {
    if (!this.documentInfo) {
      await new Promise(resolve => {
        this.eventBus.on("metadataloaded", resolve, {
          once: true,
          ...internalOpt
        });
      });
      if (pdfDocument !== this.pdfDocument) {
        return null;
      }
    }
    if (!this._contentLength) {
      await new Promise(resolve => {
        this.eventBus.on("documentloaded", resolve, {
          once: true,
          ...internalOpt
        });
      });
      if (pdfDocument !== this.pdfDocument) {
        return null;
      }
    }
    return {
      ...this.documentInfo,
      baseURL: this.baseUrl,
      filesize: this._contentLength,
      filename: this._docFilename,
      metadata: this.metadata?.getRaw(),
      authors: this.metadata?.get("dc:creator"),
      numPages: this.pagesCount,
      URL: this.url
    };
  },
  async _initializeAutoPrint(pdfDocument, openActionPromise) {
    const [openAction, jsActions] = await Promise.all([openActionPromise, this.pdfViewer.enableScripting ? null : pdfDocument.getJSActions()]);
    if (pdfDocument !== this.pdfDocument) {
      return;
    }
    let triggerAutoPrint = openAction?.get("action") === "Print";
    if (jsActions) {
      console.warn("Warning: JavaScript support is not enabled");
      for (const [name, actions] of jsActions) {
        if (triggerAutoPrint) {
          break;
        }
        switch (name) {
          case "WillClose":
          case "WillSave":
          case "DidSave":
          case "WillPrint":
          case "DidPrint":
            continue;
        }
        triggerAutoPrint = actions.some(js => AutoPrintRegExp.test(js));
      }
    }
    if (triggerAutoPrint) {
      this.triggerPrinting();
    }
  },
  async _initializeMetadata(pdfDocument) {
    const {
      info,
      metadata,
      contentDispositionFilename,
      contentLength,
      hasStructTree
    } = await pdfDocument.getMetadata();
    if (pdfDocument !== this.pdfDocument) {
      return;
    }
    this.externalServices.reportTelemetry({
      type: "taggedPDF",
      data: hasStructTree
    });
    this.documentInfo = info;
    this.metadata = metadata;
    this._contentDispositionFilename ??= contentDispositionFilename;
    this._contentLength ??= contentLength;
    console.log(`PDF ${pdfDocument.fingerprints[0]} [${info.PDFFormatVersion} ` + `${(metadata?.get("pdf:producer") || info.Producer || "-").trim()} / ` + `${(metadata?.get("xmp:creatortool") || info.Creator || "-").trim()}` + `] (PDF.js: ${version || "?"} [${build || "?"}])`);
    const pdfTitle = this._docTitle;
    if (pdfTitle) {
      this.setTitle(`${pdfTitle} - ${this._contentDispositionFilename || this._title}`);
    } else if (this._contentDispositionFilename) {
      this.setTitle(this._contentDispositionFilename);
    }
    if (info.IsXFAPresent && !info.IsAcroFormPresent && !pdfDocument.isPureXfa) {
      if (pdfDocument.loadingParams.enableXfa) {
        console.warn("Warning: XFA Foreground documents are not supported");
      } else {
        console.warn("Warning: XFA support is not enabled");
      }
    } else if ((info.IsAcroFormPresent || info.IsXFAPresent) && !this.pdfViewer.renderForms) {
      console.warn("Warning: Interactive form support is not enabled");
    }
    if (info.IsSignaturesPresent) {
      const success = this._maybeInitSignatureProperties(pdfDocument);
      if (!success) {
        console.warn("Warning: Digital signatures validation is not supported");
      }
    }
    this.eventBus.dispatch("metadataloaded", {
      source: this
    });
  },
  _maybeInitSignatureProperties(pdfDocument) {
    if (!AppOptions.get("enableSignatureVerification")) {
      return false;
    }
    const verifier = this.externalServices.createSignatureVerifier();
    if (!verifier) {
      return false;
    }
    if (pdfDocument !== this.pdfDocument) {
      return true;
    }
    this.signaturePropertiesManager ??= new SignaturePropertiesManager({
      appConfig: this.appConfig.toolbar,
      verifier,
      eventBus: this.eventBus
    });
    this.signaturePropertiesManager.setDocument(pdfDocument);
    return true;
  },
  async _initializePageLabels(pdfDocument) {
    const labels = await pdfDocument.getPageLabels();
    if (pdfDocument !== this.pdfDocument) {
      return;
    }
    if (!labels || AppOptions.get("disablePageLabels")) {
      return;
    }
    const numLabels = labels.length;
    let standardLabels = 0,
      emptyLabels = 0;
    for (let i = 0; i < numLabels; i++) {
      const label = labels[i];
      if (label === (i + 1).toString()) {
        standardLabels++;
      } else if (label === "") {
        emptyLabels++;
      } else {
        break;
      }
    }
    if (standardLabels >= numLabels || emptyLabels >= numLabels) {
      return;
    }
    const {
      pdfViewer,
      pdfThumbnailViewer,
      toolbar
    } = this;
    pdfViewer.setPageLabels(labels);
    pdfThumbnailViewer?.setPageLabels(labels);
    toolbar?.setPagesCount(numLabels, true);
    toolbar?.setPageNumber(pdfViewer.currentPageNumber, pdfViewer.currentPageLabel);
  },
  _initializePdfHistory({
    fingerprint,
    viewOnLoad,
    initialDest = null
  }) {
    if (!this.pdfHistory) {
      return;
    }
    this.pdfHistory.initialize({
      fingerprint,
      resetHistory: viewOnLoad === ViewOnLoad.INITIAL || !!this._mergedDocumentNeedsSaving,
      updateUrl: AppOptions.get("historyUpdateUrl")
    });
    if (this.pdfHistory.initialBookmark) {
      this.initialBookmark = this.pdfHistory.initialBookmark;
      this.initialRotation = this.pdfHistory.initialRotation;
    }
    if (initialDest && !this.initialBookmark && viewOnLoad === ViewOnLoad.UNKNOWN) {
      this.initialBookmark = JSON.stringify(initialDest);
      this.pdfHistory.push({
        explicitDest: initialDest,
        pageNumber: null
      });
    }
  },
  _hasChanges() {
    return this.pdfDocument?.annotationStorage.size > 0 || this.pdfThumbnailViewer?.hasStructuralChanges() || this._mergedDocumentNeedsSaving === true;
  },
  _initializeAnnotationStorageCallbacks(pdfDocument) {
    if (pdfDocument !== this.pdfDocument) {
      return;
    }
    const {
      annotationStorage
    } = pdfDocument;
    annotationStorage.onSetModified = () => {
      this._annotationStorageModified = true;
    };
    annotationStorage.onResetModified = () => {
      delete this._annotationStorageModified;
    };
    annotationStorage.onAnnotationEditor = typeStr => {
      this._hasAnnotationEditors = !!typeStr;
      this.setTitle();
    };
  },
  setInitialView(storedHash, {
    rotation,
    sidebarView,
    scrollMode,
    spreadMode
  } = {}) {
    const setRotation = angle => {
      if (isValidRotation(angle)) {
        this.pdfViewer.pagesRotation = angle;
      }
    };
    const setViewerModes = (scroll, spread) => {
      if (isValidScrollMode(scroll)) {
        this.pdfViewer.scrollMode = scroll;
      }
      if (isValidSpreadMode(spread)) {
        this.pdfViewer.spreadMode = spread;
      }
    };
    this.isInitialViewSet = true;
    this.viewsManager?.setInitialView(sidebarView);
    setViewerModes(scrollMode, spreadMode);
    if (this.initialBookmark) {
      setRotation(this.initialRotation);
      delete this.initialRotation;
      this.pdfLinkService.setHash(this.initialBookmark);
      this.initialBookmark = null;
    } else if (storedHash) {
      setRotation(rotation);
      this.pdfLinkService.setHash(storedHash);
    }
    this.toolbar?.setPageNumber(this.pdfViewer.currentPageNumber, this.pdfViewer.currentPageLabel);
    this.secondaryToolbar?.setPageNumber(this.pdfViewer.currentPageNumber);
    this.pdfViewer.currentScaleValue ||= (/* inlined export .DEFAULT_SCALE_VALUE */"auto");
  },
  _cleanup() {
    if (!this.pdfDocument) {
      return;
    }
    this.pdfViewer.cleanup();
    this.pdfThumbnailViewer?.cleanup();
    this.pdfDocument.cleanup(AppOptions.get("fontExtraProperties"));
  },
  forceRendering() {
    this.pdfRenderingQueue.printing = !!this.printService;
    this.pdfRenderingQueue.isThumbnailViewEnabled = this.viewsManager?.visibleView === SidebarView.THUMBS;
    this.pdfRenderingQueue.renderHighestPriority();
  },
  beforePrint() {
    this._printAnnotationStoragePromise = this.pdfScriptingManager.dispatchWillPrint().catch(() => {}).then(() => this.pdfDocument?.annotationStorage.print);
    if (this.printService) {
      return;
    }
    if (!this.supportsPrinting || !this.pdfViewer.printingAllowed) {
      this._otherError("pdfjs-printing-not-supported");
      return;
    }
    if (!this.pdfViewer.pageViewsReady) {
      this.l10n.get("pdfjs-printing-not-ready").then(msg => {
        window.alert(msg);
      });
      return;
    }
    this.printService = PDFPrintServiceFactory.createPrintService({
      pdfDocument: this.pdfDocument,
      pagesOverview: this.pdfViewer.getPagesOverview(),
      printContainer: this.appConfig.printContainer,
      printResolution: AppOptions.get("printResolution"),
      printAnnotationStoragePromise: this._printAnnotationStoragePromise
    });
    this.forceRendering();
    this.setTitle();
    this.printService.layout();
    if (this._hasAnnotationEditors) {
      this.externalServices.reportTelemetry({
        type: "editing",
        data: {
          type: "print",
          stats: this.pdfDocument?.annotationStorage.editorStats
        }
      });
    }
  },
  afterPrint() {
    if (this._printAnnotationStoragePromise) {
      this._printAnnotationStoragePromise.then(() => {
        this.pdfScriptingManager.dispatchDidPrint();
      });
      this._printAnnotationStoragePromise = null;
    }
    if (this.printService) {
      this.printService.destroy();
      this.printService = null;
      this.pdfDocument?.annotationStorage.resetModified();
    }
    this.forceRendering();
    this.setTitle();
  },
  rotatePages(delta) {
    this.pdfViewer.pagesRotation += delta;
  },
  requestPresentationMode() {
    this.pdfPresentationMode?.request();
  },
  async triggerPrinting() {
    if (this.supportsPrinting && (await this._printPermissionPromise)) {
      window.print();
    }
  },
  bindEvents() {
    if (this._eventBusAC) {
      return;
    }
    const ac = this._eventBusAC = new AbortController();
    const opts = {
      signal: ac.signal,
      ...internalOpt
    };
    const {
      eventBus,
      externalServices,
      pdfDocumentProperties,
      pdfViewer,
      preferences
    } = this;
    eventBus.on("resize", onResize.bind(this), opts);
    eventBus.on("hashchange", onHashchange.bind(this), opts);
    eventBus.on("beforeprint", this.beforePrint.bind(this), opts);
    eventBus.on("afterprint", this.afterPrint.bind(this), opts);
    eventBus.on("pagerender", onPageRender.bind(this), opts);
    eventBus.on("pagerendered", onPageRendered.bind(this), opts);
    eventBus.on("updateviewarea", onUpdateViewarea.bind(this), opts);
    eventBus.on("pagechanging", onPageChanging.bind(this), opts);
    eventBus.on("scalechanging", onScaleChanging.bind(this), opts);
    eventBus.on("rotationchanging", onRotationChanging.bind(this), opts);
    eventBus.on("sidebarviewchanged", onSidebarViewChanged.bind(this), opts);
    eventBus.on("pagemode", onPageMode.bind(this), opts);
    eventBus.on("namedaction", onNamedAction.bind(this), opts);
    eventBus.on("presentationmodechanged", evt => pdfViewer.presentationModeState = evt.state, opts);
    eventBus.on("presentationmode", this.requestPresentationMode.bind(this), opts);
    eventBus.on("switchannotationeditormode", evt => pdfViewer.annotationEditorMode = evt, opts);
    eventBus.on("print", this.triggerPrinting.bind(this), opts);
    eventBus.on("download", this.downloadOrSave.bind(this), opts);
    eventBus.on("firstpage", () => this.page = 1, opts);
    eventBus.on("lastpage", () => this.page = this.pagesCount, opts);
    eventBus.on("nextpage", () => pdfViewer.nextPage(), opts);
    eventBus.on("previouspage", () => pdfViewer.previousPage(), opts);
    eventBus.on("zoomin", this.zoomIn.bind(this), opts);
    eventBus.on("zoomout", this.zoomOut.bind(this), opts);
    eventBus.on("zoomreset", this.zoomReset.bind(this), opts);
    eventBus.on("pagenumberchanged", onPageNumberChanged.bind(this), opts);
    eventBus.on("scalechanged", evt => pdfViewer.currentScaleValue = evt.value, opts);
    eventBus.on("rotatecw", this.rotatePages.bind(this, 90), opts);
    eventBus.on("rotateccw", this.rotatePages.bind(this, -90), opts);
    eventBus.on("optionalcontentconfig", evt => pdfViewer.optionalContentConfigPromise = evt.promise, opts);
    eventBus.on("switchscrollmode", evt => pdfViewer.scrollMode = evt.mode, opts);
    eventBus.on("scrollmodechanged", onViewerModesChanged.bind(this, "scrollMode"), opts);
    eventBus.on("switchspreadmode", evt => pdfViewer.spreadMode = evt.mode, opts);
    eventBus.on("spreadmodechanged", onViewerModesChanged.bind(this, "spreadMode"), opts);
    eventBus.on("imagealttextsettings", onImageAltTextSettings.bind(this), opts);
    eventBus.on("documentproperties", () => pdfDocumentProperties?.open(), opts);
    eventBus.on("findfromurlhash", onFindFromUrlHash.bind(this), opts);
    eventBus.on("updatefindmatchescount", onUpdateFindMatchesCount.bind(this), opts);
    eventBus.on("updatefindcontrolstate", onUpdateFindControlState.bind(this), opts);
    eventBus.on("fileinputchange", onFileInputChange.bind(this), opts);
    eventBus.on("openfile", onOpenFile.bind(this), opts);
    eventBus.on("pagesedited", this.onPagesEdited.bind(this), opts);
    eventBus.on("saveextractedpages", this.onSavePages.bind(this), opts);
    eventBus.on("saveandload", this.onSaveAndLoad.bind(this), opts);
  },
  bindWindowEvents() {
    if (this._windowAC) {
      return;
    }
    this._windowAC = new AbortController();
    const {
      eventBus,
      appConfig: {
        mainContainer
      },
      pdfViewer,
      _windowAC: {
        signal
      }
    } = this;
    this._touchManager = new TouchManager({
      container: window,
      isPinchingDisabled: () => pdfViewer.isInPresentationMode,
      isPinchingStopped: () => this.overlayManager?.active,
      onPinching: this.touchPinchCallback.bind(this),
      onPinchEnd: this.touchPinchEndCallback.bind(this),
      onPanning: this.touchPanCallback.bind(this),
      signal
    });
    function addWindowResolutionChange(evt = null) {
      if (evt) {
        pdfViewer.refresh();
      }
      const mediaQueryList = window.matchMedia(`(resolution: ${OutputScale.pixelRatio}dppx)`);
      mediaQueryList.addEventListener("change", addWindowResolutionChange, {
        once: true,
        signal
      });
    }
    addWindowResolutionChange();
    window.addEventListener("wheel", onWheel.bind(this), {
      passive: false,
      signal
    });
    window.addEventListener("click", onClick.bind(this), {
      signal
    });
    window.addEventListener("keydown", onKeyDown.bind(this), {
      signal
    });
    window.addEventListener("keyup", onKeyUp.bind(this), {
      signal
    });
    window.addEventListener("resize", () => eventBus.dispatch("resize", {
      source: window
    }), {
      signal
    });
    window.addEventListener("hashchange", () => {
      eventBus.dispatch("hashchange", {
        source: window,
        hash: document.location.hash.substring(1)
      });
    }, {
      signal
    });
    window.addEventListener("beforeprint", () => eventBus.dispatch("beforeprint", {
      source: window
    }), {
      signal
    });
    window.addEventListener("afterprint", () => eventBus.dispatch("afterprint", {
      source: window
    }), {
      signal
    });
    window.addEventListener("updatefromsandbox", evt => {
      eventBus.dispatch("updatefromsandbox", {
        source: window,
        detail: evt.detail
      });
    }, {
      signal
    });
    window.addEventListener("beforeunload", onBeforeUnload.bind(this), {
      signal
    });
    if (!("onscrollend" in document.documentElement)) {
      return;
    }
    ({
      scrollTop: this._lastScrollTop,
      scrollLeft: this._lastScrollLeft
    } = mainContainer);
    let scrollendTimeoutID, scrollAbortController;
    const scrollend = () => {
      ({
        scrollTop: this._lastScrollTop,
        scrollLeft: this._lastScrollLeft
      } = mainContainer);
      clearTimeout(scrollendTimeoutID);
      if (this._isScrolling) {
        scrollAbortController.abort();
        scrollAbortController = null;
        this._isScrolling = false;
      }
    };
    const scroll = () => {
      if (this._isCtrlKeyDown) {
        return;
      }
      if (this._lastScrollTop === mainContainer.scrollTop && this._lastScrollLeft === mainContainer.scrollLeft) {
        return;
      }
      if (!this._isScrolling) {
        scrollAbortController = new AbortController();
        const abortSignal = AbortSignal.any([scrollAbortController.signal, signal]);
        mainContainer.addEventListener("scrollend", scrollend, {
          signal: abortSignal
        });
        mainContainer.addEventListener("blur", scrollend, {
          signal: abortSignal
        });
        this._isScrolling = true;
      }
      clearTimeout(scrollendTimeoutID);
      scrollendTimeoutID = setTimeout(scrollend, 100);
    };
    mainContainer.addEventListener("scroll", scroll, {
      passive: true,
      signal
    });
  },
  unbindEvents() {
    this._eventBusAC?.abort();
    this._eventBusAC = null;
  },
  unbindWindowEvents() {
    this._windowAC?.abort();
    this._windowAC = null;
    this._touchManager = null;
  },
  async testingClose() {
    this.unbindEvents();
    this.unbindWindowEvents();
    this._globalAbortController?.abort();
    this._globalAbortController = null;
    this.findBar?.close();
    await Promise.all([this.l10n?.destroy(), this.close()]);
  },
  onPagesEdited(data) {
    this.pdfViewer.onPagesEdited(data);
  },
  async onSavePages({
    data: {
      pageInfos,
      copyLevels
    }
  }) {
    if (!this.downloadManager || !this.pdfDocument) {
      return;
    }
    const modifiedPdfBytes = await this.pdfDocument.extractPages(pageInfos, copyLevels);
    if (!modifiedPdfBytes) {
      console.error("Something wrong happened when saving the edited PDF.\nPlease file a bug.");
      return;
    }
    this.downloadManager.download(modifiedPdfBytes, this._downloadUrl, this._docFilename, true);
  },
  async onSaveAndLoad({
    data: {
      pageInfos,
      copyLevels
    }
  }) {
    if (!this.pdfDocument) {
      return;
    }
    const modifiedPdfBytes = await this.pdfDocument.extractPages(pageInfos, copyLevels);
    if (!modifiedPdfBytes) {
      console.error("Something wrong happened when saving the edited PDF.\nPlease file a bug.");
      return;
    }
    this._mergedDocumentNeedsSaving = true;
    const downloadUrl = this._downloadUrl;
    await this.open({
      data: modifiedPdfBytes,
      filename: this._docFilename
    });
    this._downloadUrl = downloadUrl;
    this._isMergedDocument = true;
  },
  _accumulateTicks(ticks, prop) {
    if (this[prop] > 0 && ticks < 0 || this[prop] < 0 && ticks > 0) {
      this[prop] = 0;
    }
    this[prop] += ticks;
    const wholeTicks = Math.trunc(this[prop]);
    this[prop] -= wholeTicks;
    return wholeTicks;
  },
  _accumulateFactor(previousScale, factor, prop) {
    if (factor === 1) {
      return 1;
    }
    const target = MathClamp(previousScale * factor * this[prop], (/* inlined export .MIN_SCALE */0.1), (/* inlined export .MAX_SCALE */25));
    const newScale = Math.round(target * 100) / 100;
    this[prop] = target / newScale;
    return newScale / previousScale;
  },
  _unblockDocumentLoadEvent() {
    document.blockUnblockOnload?.(false);
    this._unblockDocumentLoadEvent = () => {};
  },
  get scriptingReady() {
    return this.pdfScriptingManager.ready;
  }
};
initCom(PDFViewerApplication);
PDFPrintServiceFactory.initGlobals(PDFViewerApplication);
{
  const HOSTED_VIEWER_ORIGINS = new Set(["null", "http://mozilla.github.io", "https://mozilla.github.io"]);
  var validateFileURL = function (file) {
    if (!file) {
      return;
    }
    const viewerOrigin = URL.parse(window.location)?.origin || "null";
    if (HOSTED_VIEWER_ORIGINS.has(viewerOrigin)) {
      return;
    }
    const fileOrigin = URL.parse(file, window.location)?.origin;
    if (fileOrigin === viewerOrigin) {
      return;
    }
    const ex = new Error("file origin does not match viewer's");
    PDFViewerApplication._documentError("pdfjs-loading-error", {
      message: ex.message
    });
    throw ex;
  };
  var onFileInputChange = function (evt) {
    if (this.pdfViewer?.isInPresentationMode) {
      return;
    }
    const file = evt.fileInput.files[0];
    this.open({
      url: URL.createObjectURL(file),
      originalUrl: encodeURIComponent(file.name)
    });
  };
  var onOpenFile = function (evt) {
    this._openFileInput?.click();
  };
}
function onPageRender({
  pageNumber
}) {
  if (pageNumber === this.page) {
    this.toolbar?.updateLoadingIndicatorState(true);
  }
}
function onPageRendered({
  pageNumber,
  isDetailView,
  error
}) {
  if (pageNumber === this.page) {
    this.toolbar?.updateLoadingIndicatorState(false);
  }
  if (!isDetailView && this.viewsManager?.visibleView === SidebarView.THUMBS) {
    const pageView = this.pdfViewer.getPageView(pageNumber - 1);
    const thumbnailView = this.pdfThumbnailViewer?.getThumbnail(pageNumber - 1);
    if (pageView) {
      thumbnailView?.setImage(pageView);
    }
  }
  if (error) {
    this._otherError("pdfjs-rendering-error", error);
  }
}
function onPageMode({
  mode
}) {
  let view;
  switch (mode) {
    case "thumbs":
      view = SidebarView.THUMBS;
      break;
    case "bookmarks":
    case "outline":
      view = SidebarView.OUTLINE;
      break;
    case "attachments":
      view = SidebarView.ATTACHMENTS;
      break;
    case "layers":
      view = SidebarView.LAYERS;
      break;
    case "none":
      view = SidebarView.NONE;
      break;
    default:
      console.error('Invalid "pagemode" hash parameter: ' + mode);
      return;
  }
  this.viewsManager?.switchView(view, true);
}
function onNamedAction(evt) {
  switch (evt.action) {
    case "GoToPage":
      this.appConfig.toolbar?.pageNumber.select();
      break;
    case "Find":
      if (!this.supportsIntegratedFind) {
        this.findBar?.toggle();
      }
      break;
    case "Print":
      this.triggerPrinting();
      break;
    case "SaveAs":
      this.downloadOrSave();
      break;
  }
}
function onSidebarViewChanged({
  view
}) {
  this.pdfRenderingQueue.isThumbnailViewEnabled = view === SidebarView.THUMBS;
  if (this.isInitialViewSet) {
    this.store?.setMultiple({
      sidebarView: view
    }).catch(() => {});
  }
}
function onUpdateViewarea({
  location
}) {
  if (this.isInitialViewSet) {
    this.store?.setMultiple({
      page: location.pageNumber,
      zoom: location.scale,
      scrollLeft: location.left,
      scrollTop: location.top,
      rotation: location.rotation
    }).catch(() => {});
  }
  if (this.appConfig.secondaryToolbar) {
    this.appConfig.secondaryToolbar.viewBookmarkButton.href = this.pdfLinkService.getAnchorUrl(location.pdfOpenParams);
  }
}
function onViewerModesChanged(name, evt) {
  if (this.isInitialViewSet && !this.pdfViewer.isInPresentationMode) {
    this.store?.setMultiple({
      [name]: evt.mode
    }).catch(() => {});
  }
}
function onResize() {
  const {
    pdfDocument,
    pdfViewer,
    pdfRenderingQueue
  } = this;
  if (pdfRenderingQueue.printing && window.matchMedia("print").matches) {
    return;
  }
  if (!pdfDocument) {
    return;
  }
  const currentScaleValue = pdfViewer.currentScaleValue;
  if (currentScaleValue === "auto" || currentScaleValue === "page-fit" || currentScaleValue === "page-width") {
    pdfViewer.currentScaleValue = currentScaleValue;
  }
  pdfViewer.update();
}
function onHashchange(evt) {
  const hash = evt.hash;
  if (!hash) {
    return;
  }
  if (!this.isInitialViewSet) {
    this.initialBookmark = hash;
  } else if (!this.pdfHistory?.popStateInProgress) {
    this.pdfLinkService.setHash(hash);
  }
}
function onPageNumberChanged(evt) {
  const {
    pdfViewer
  } = this;
  if (evt.value !== "") {
    this.pdfLinkService.goToPage(evt.value);
  }
  if (evt.value !== pdfViewer.currentPageNumber.toString() && evt.value !== pdfViewer.currentPageLabel) {
    this.toolbar?.setPageNumber(pdfViewer.currentPageNumber, pdfViewer.currentPageLabel);
  }
}
function onImageAltTextSettings() {
  this.imageAltTextSettings?.open({
    enableGuessAltText: AppOptions.get("enableGuessAltText"),
    enableNewAltTextWhenAddingImage: AppOptions.get("enableNewAltTextWhenAddingImage")
  });
}
function onFindFromUrlHash(evt) {
  this.eventBus.dispatch("find", {
    source: evt.source,
    type: "",
    query: evt.query,
    caseSensitive: false,
    entireWord: false,
    highlightAll: true,
    findPrevious: false,
    matchDiacritics: true
  });
}
function onUpdateFindMatchesCount({
  matchesCount
}) {
  if (this.supportsIntegratedFind) {
    this.externalServices.updateFindMatchesCount(matchesCount);
  } else {
    this.findBar?.updateResultsCount(matchesCount);
  }
}
function onUpdateFindControlState({
  state,
  previous,
  entireWord,
  matchesCount,
  rawQuery
}) {
  if (this.supportsIntegratedFind) {
    this.externalServices.updateFindControlState({
      result: state,
      findPrevious: previous,
      entireWord,
      matchesCount,
      rawQuery
    });
  } else {
    this.findBar?.updateUIState(state, previous, matchesCount);
  }
}
function onScaleChanging(evt) {
  this.toolbar?.setPageScale(evt.presetValue, evt.scale);
  this.pdfViewer.update();
}
function onRotationChanging(evt) {
  if (this.pdfThumbnailViewer) {
    this.pdfThumbnailViewer.pagesRotation = evt.pagesRotation;
  }
  this.forceRendering();
  this.pdfViewer.currentPageNumber = evt.pageNumber;
}
function onPageChanging({
  pageNumber,
  pageLabel
}) {
  this.toolbar?.setPageNumber(pageNumber, pageLabel);
  this.secondaryToolbar?.setPageNumber(pageNumber);
  if (this.viewsManager?.visibleView === SidebarView.THUMBS) {
    this.pdfThumbnailViewer?.scrollThumbnailIntoView(pageNumber);
  }
  const currentPage = this.pdfViewer.getPageView(pageNumber - 1);
  this.toolbar?.updateLoadingIndicatorState(currentPage?.renderingState === RenderingStates.RUNNING);
}
function onWheel(evt) {
  const {
    pdfViewer,
    supportsMouseWheelZoomCtrlKey,
    supportsMouseWheelZoomMetaKey,
    supportsPinchToZoom
  } = this;
  if (pdfViewer.isInPresentationMode) {
    return;
  }
  const deltaMode = evt.deltaMode;
  let scaleFactor = Math.exp(-evt.deltaY / 100);
  const isBuiltInMac = false;
  const isPinchToZoom = evt.ctrlKey && !this._isCtrlKeyDown && deltaMode === WheelEvent.DOM_DELTA_PIXEL && evt.deltaX === 0 && (Math.abs(scaleFactor - 1) < 0.05 || isBuiltInMac) && evt.deltaZ === 0;
  const origin = [evt.clientX, evt.clientY];
  if (isPinchToZoom || evt.ctrlKey && supportsMouseWheelZoomCtrlKey || evt.metaKey && supportsMouseWheelZoomMetaKey) {
    evt.preventDefault();
    if (this._isScrolling || document.visibilityState === "hidden" || this.overlayManager.active) {
      return;
    }
    if (isPinchToZoom && supportsPinchToZoom) {
      scaleFactor = this._accumulateFactor(pdfViewer.currentScale, scaleFactor, "_wheelUnusedFactor");
      this.updateZoom(null, scaleFactor, origin);
    } else {
      const delta = normalizeWheelEventDirection(evt);
      let ticks = 0;
      if (deltaMode === WheelEvent.DOM_DELTA_LINE || deltaMode === WheelEvent.DOM_DELTA_PAGE) {
        ticks = Math.abs(delta) >= 1 ? Math.sign(delta) : this._accumulateTicks(delta, "_wheelUnusedTicks");
      } else {
        const PIXELS_PER_LINE_SCALE = 30;
        ticks = this._accumulateTicks(delta / PIXELS_PER_LINE_SCALE, "_wheelUnusedTicks");
      }
      this.updateZoom(ticks, null, origin);
    }
  }
}
function closeSecondaryToolbar({
  target
}) {
  if (!this.secondaryToolbar?.isOpen) {
    return;
  }
  const {
    toolbar,
    secondaryToolbar
  } = this.appConfig;
  if (this.pdfViewer.containsElement(target) || toolbar?.container.contains(target) && !secondaryToolbar?.toolbar.contains(target) && !secondaryToolbar?.toggleButton.contains(target)) {
    this.secondaryToolbar.close();
  }
}
function closeEditorUndoBar(evt) {
  if (!this.editorUndoBar?.isOpen) {
    return;
  }
  if (this.appConfig.secondaryToolbar?.toolbar.contains(evt.target)) {
    this.editorUndoBar.hide();
  }
}
function closeSignatureProperties({
  target
}) {
  if (this.signaturePropertiesManager?.shouldCloseOnClick(target)) {
    this.signaturePropertiesManager.close();
  }
}
function onBeforeUnload(evt) {
  if (this._hasChanges()) {
    evt.preventDefault();
    evt.returnValue = "";
    return false;
  }
  return true;
}
function onClick(evt) {
  closeSecondaryToolbar.call(this, evt);
  closeEditorUndoBar.call(this, evt);
  closeSignatureProperties.call(this, evt);
}
function onKeyUp(evt) {
  if (evt.key === "Control") {
    this._isCtrlKeyDown = false;
  }
}
function onKeyDown(evt) {
  this._isCtrlKeyDown = evt.key === "Control";
  if (this.editorUndoBar?.isOpen && evt.keyCode !== 9 && evt.keyCode !== 16 && !((evt.keyCode === 13 || evt.keyCode === 32) && getActiveOrFocusedElement() === this.appConfig.editorUndoBar.undoButton)) {
    this.editorUndoBar.hide();
  }
  if (this.overlayManager.active) {
    return;
  }
  const {
    eventBus,
    pdfViewer
  } = this;
  const isViewerInPresentationMode = pdfViewer.isInPresentationMode;
  let handled = false,
    ensureViewerFocused = false;
  const cmd = (evt.ctrlKey ? 1 : 0) | (evt.altKey ? 2 : 0) | (evt.shiftKey ? 4 : 0) | (evt.metaKey ? 8 : 0);
  if (cmd === 1 || cmd === 8 || cmd === 5 || cmd === 12) {
    switch (evt.keyCode) {
      case 70:
        if (!this.supportsIntegratedFind && !evt.shiftKey) {
          this.findBar?.open();
          handled = true;
        }
        break;
      case 71:
        if (!this.supportsIntegratedFind) {
          const {
            state
          } = this.findController;
          if (state) {
            const newState = {
              source: window,
              type: "again",
              findPrevious: cmd === 5 || cmd === 12
            };
            eventBus.dispatch("find", {
              ...state,
              ...newState
            });
          }
          handled = true;
        }
        break;
      case 61:
      case 107:
      case 187:
      case 171:
        this.zoomIn();
        handled = true;
        break;
      case 173:
      case 109:
      case 189:
        this.zoomOut();
        handled = true;
        break;
      case 48:
      case 96:
        if (!isViewerInPresentationMode) {
          setTimeout(() => {
            this.zoomReset();
          });
          handled = false;
        }
        break;
      case 38:
        if (isViewerInPresentationMode || this.page > 1) {
          this.page = 1;
          handled = true;
          ensureViewerFocused = true;
        }
        break;
      case 40:
        if (isViewerInPresentationMode || this.page < this.pagesCount) {
          this.page = this.pagesCount;
          handled = true;
          ensureViewerFocused = true;
        }
        break;
    }
  }
  if (cmd === 1 || cmd === 8) {
    switch (evt.keyCode) {
      case 83:
        eventBus.dispatch("download", {
          source: window
        });
        handled = true;
        break;
      case 79:
        {
          eventBus.dispatch("openfile", {
            source: window
          });
          handled = true;
        }
        break;
    }
  }
  if (cmd === 3 || cmd === 10) {
    switch (evt.keyCode) {
      case 80:
        this.requestPresentationMode();
        handled = true;
        this.externalServices.reportTelemetry({
          type: "buttons",
          data: {
            id: "presentationModeKeyboard"
          }
        });
        break;
      case 71:
        if (this.appConfig.toolbar) {
          this.appConfig.toolbar.pageNumber.select();
          handled = true;
        }
        break;
    }
  }
  if (handled) {
    if (ensureViewerFocused && !isViewerInPresentationMode) {
      pdfViewer.focus();
    }
    evt.preventDefault();
    return;
  }
  const curElement = getActiveOrFocusedElement();
  const curElementTagName = curElement?.tagName.toUpperCase();
  if (curElementTagName === "INPUT" || curElementTagName === "TEXTAREA" || curElementTagName === "SELECT" || curElementTagName === "BUTTON" && evt.keyCode === 32 || curElement?.isContentEditable) {
    if (evt.keyCode !== 27) {
      return;
    }
  }
  if (cmd === 0) {
    let turnPage = 0,
      turnOnlyIfPageFit = false;
    switch (evt.keyCode) {
      case 38:
        if (this.supportsCaretBrowsingMode) {
          this.moveCaret(true, false);
          handled = true;
          break;
        }
      case 33:
        if (pdfViewer.isVerticalScrollbarEnabled) {
          turnOnlyIfPageFit = true;
        }
        turnPage = -1;
        break;
      case 8:
        if (!isViewerInPresentationMode) {
          turnOnlyIfPageFit = true;
        }
        turnPage = -1;
        break;
      case 37:
        if (this.supportsCaretBrowsingMode) {
          return;
        }
        if (pdfViewer.isHorizontalScrollbarEnabled) {
          turnOnlyIfPageFit = true;
        }
      case 75:
      case 80:
        turnPage = -1;
        break;
      case 27:
        if (this.secondaryToolbar?.isOpen) {
          this.secondaryToolbar.close();
          handled = true;
        }
        if (this.signaturePropertiesManager?.isOpen) {
          this.signaturePropertiesManager.close();
          handled = true;
        }
        if (!this.supportsIntegratedFind && this.findBar?.opened) {
          this.findBar.close();
          handled = true;
        }
        break;
      case 40:
        if (this.supportsCaretBrowsingMode) {
          this.moveCaret(false, false);
          handled = true;
          break;
        }
      case 34:
        if (pdfViewer.isVerticalScrollbarEnabled) {
          turnOnlyIfPageFit = true;
        }
        turnPage = 1;
        break;
      case 32:
        if (!isViewerInPresentationMode) {
          turnOnlyIfPageFit = true;
        }
        turnPage = 1;
        break;
      case 39:
        if (this.supportsCaretBrowsingMode) {
          return;
        }
        if (pdfViewer.isHorizontalScrollbarEnabled) {
          turnOnlyIfPageFit = true;
        }
      case 74:
      case 78:
        turnPage = 1;
        break;
      case 36:
        if (isViewerInPresentationMode || this.page > 1) {
          this.page = 1;
          handled = true;
          ensureViewerFocused = true;
        }
        break;
      case 35:
        if (isViewerInPresentationMode || this.page < this.pagesCount) {
          this.page = this.pagesCount;
          handled = true;
          ensureViewerFocused = true;
        }
        break;
      case 83:
        this.pdfCursorTools?.switchTool(CursorTool.SELECT);
        break;
      case 72:
        this.pdfCursorTools?.switchTool(CursorTool.HAND);
        break;
      case 82:
        this.rotatePages(90);
        break;
      case 115:
        this.viewsManager?.toggle();
        break;
    }
    if (turnPage !== 0 && (!turnOnlyIfPageFit || pdfViewer.currentScaleValue === "page-fit")) {
      if (turnPage > 0) {
        pdfViewer.nextPage();
      } else {
        pdfViewer.previousPage();
      }
      handled = true;
    }
  }
  if (cmd === 4) {
    switch (evt.keyCode) {
      case 32:
        if (!isViewerInPresentationMode && pdfViewer.currentScaleValue !== "page-fit") {
          break;
        }
        pdfViewer.previousPage();
        handled = true;
        break;
      case 38:
        this.moveCaret(true, true);
        handled = true;
        break;
      case 40:
        this.moveCaret(false, true);
        handled = true;
        break;
      case 82:
        this.rotatePages(-90);
        break;
    }
  }
  if (!handled && !isViewerInPresentationMode) {
    if (evt.keyCode >= 33 && evt.keyCode <= 40 || evt.keyCode === 32 && curElementTagName !== "BUTTON") {
      ensureViewerFocused = true;
    }
  }
  if (ensureViewerFocused && !pdfViewer.containsElement(curElement)) {
    pdfViewer.focus();
  }
  if (handled) {
    evt.preventDefault();
  }
}

;// ./web/viewer.js





const AppConstants = {
  LinkTarget: LinkTarget,
  RenderingStates: RenderingStates,
  ScrollMode: ScrollMode,
  SpreadMode: SpreadMode
};
window.PDFViewerApplication = PDFViewerApplication;
window.PDFViewerApplicationConstants = AppConstants;
window.PDFViewerApplicationOptions = AppOptions;
function getViewerConfiguration() {
  return {
    appContainer: document.body,
    principalContainer: document.getElementById("mainContainer"),
    mainContainer: document.getElementById("viewerContainer"),
    viewerContainer: document.getElementById("viewer"),
    viewerAlert: document.getElementById("viewer-alert"),
    toolbar: {
      container: document.getElementById("toolbarContainer"),
      numPages: document.getElementById("numPages"),
      pageNumber: document.getElementById("pageNumber"),
      scaleSelect: document.getElementById("scaleSelect"),
      customScaleOption: document.getElementById("customScaleOption"),
      previous: document.getElementById("previous"),
      next: document.getElementById("next"),
      zoomIn: document.getElementById("zoomInButton"),
      zoomOut: document.getElementById("zoomOutButton"),
      print: document.getElementById("printButton"),
      editorCommentButton: document.getElementById("editorCommentButton"),
      editorCommentParamsToolbar: document.getElementById("editorCommentParamsToolbar"),
      editorFreeTextButton: document.getElementById("editorFreeTextButton"),
      editorFreeTextParamsToolbar: document.getElementById("editorFreeTextParamsToolbar"),
      editorHighlightButton: document.getElementById("editorHighlightButton"),
      editorHighlightParamsToolbar: document.getElementById("editorHighlightParamsToolbar"),
      editorHighlightColorPicker: document.getElementById("editorHighlightColorPicker"),
      editorInkButton: document.getElementById("editorInkButton"),
      editorInkParamsToolbar: document.getElementById("editorInkParamsToolbar"),
      editorStampButton: document.getElementById("editorStampButton"),
      editorStampParamsToolbar: document.getElementById("editorStampParamsToolbar"),
      editorSignatureButton: document.getElementById("editorSignatureButton"),
      editorSignatureParamsToolbar: document.getElementById("editorSignatureParamsToolbar"),
      signaturePropertiesButton: document.getElementById("signaturePropertiesButton"),
      signaturePropertiesPanel: document.getElementById("signaturePropertiesPanel"),
      signaturePropertiesContainer: document.getElementById("signaturePropertiesContainer"),
      signaturePropertiesBanner: document.getElementById("signaturePropertiesBanner"),
      signaturePropertiesList: document.getElementById("signaturePropertiesList"),
      signaturePropertiesSeparator: document.getElementById("signaturePropertiesSeparator"),
      download: document.getElementById("downloadButton")
    },
    secondaryToolbar: {
      toolbar: document.getElementById("secondaryToolbar"),
      toggleButton: document.getElementById("secondaryToolbarToggleButton"),
      presentationModeButton: document.getElementById("presentationMode"),
      openFileButton: document.getElementById("secondaryOpenFile"),
      printButton: document.getElementById("secondaryPrint"),
      downloadButton: document.getElementById("secondaryDownload"),
      viewBookmarkButton: document.getElementById("viewBookmark"),
      firstPageButton: document.getElementById("firstPage"),
      lastPageButton: document.getElementById("lastPage"),
      pageRotateCwButton: document.getElementById("pageRotateCw"),
      pageRotateCcwButton: document.getElementById("pageRotateCcw"),
      cursorSelectToolButton: document.getElementById("cursorSelectTool"),
      cursorHandToolButton: document.getElementById("cursorHandTool"),
      scrollPageButton: document.getElementById("scrollPage"),
      scrollVerticalButton: document.getElementById("scrollVertical"),
      scrollHorizontalButton: document.getElementById("scrollHorizontal"),
      scrollWrappedButton: document.getElementById("scrollWrapped"),
      spreadNoneButton: document.getElementById("spreadNone"),
      spreadOddButton: document.getElementById("spreadOdd"),
      spreadEvenButton: document.getElementById("spreadEven"),
      imageAltTextSettingsButton: document.getElementById("imageAltTextSettings"),
      imageAltTextSettingsSeparator: document.getElementById("imageAltTextSettingsSeparator"),
      documentPropertiesButton: document.getElementById("documentProperties")
    },
    viewsManager: {
      outerContainer: document.getElementById("outerContainer"),
      toggleButton: document.getElementById("viewsManagerToggleButton"),
      sidebarContainer: document.getElementById("viewsManager"),
      resizer: document.getElementById("viewsManagerResizer"),
      thumbnailButton: document.getElementById("thumbnailsViewMenu"),
      outlineButton: document.getElementById("outlinesViewMenu"),
      attachmentsButton: document.getElementById("attachmentsViewMenu"),
      layersButton: document.getElementById("layersViewMenu"),
      viewsManagerSelectorButton: document.getElementById("viewsManagerSelectorButton"),
      viewsManagerSelectorOptions: document.getElementById("viewsManagerSelectorOptions"),
      thumbnailsView: document.getElementById("thumbnailsView"),
      outlinesView: document.getElementById("outlinesView"),
      attachmentsView: document.getElementById("attachmentsView"),
      layersView: document.getElementById("layersView"),
      viewsManagerAddFile: {
        button: document.getElementById("viewsManagerAddFileButton"),
        picker: document.getElementById("viewsManagerAddFilePicker")
      },
      viewsManagerCurrentOutlineButton: document.getElementById("viewsManagerCurrentOutlineButton"),
      viewsManagerHeaderLabel: document.getElementById("viewsManagerHeaderLabel"),
      viewsManagerStatus: document.getElementById("viewsManagerStatus"),
      viewsManagerStatusBar: {
        viewsManagerStatusAction: document.getElementById("viewsManagerStatusAction"),
        viewsManagerStatusActionDeselectButton: document.getElementById("viewsManagerStatusActionDeselectButton"),
        viewsManagerStatusActionLabel: document.getElementById("viewsManagerStatusActionLabel")
      },
      viewsManagerUndoBar: {
        viewsManagerStatusUndo: document.getElementById("viewsManagerStatusUndo"),
        viewsManagerStatusUndoLabel: document.getElementById("viewsManagerStatusUndoLabel"),
        viewsManagerStatusUndoButton: document.getElementById("viewsManagerStatusUndoButton"),
        viewsManagerStatusUndoCloseButton: document.getElementById("viewsManagerStatusUndoCloseButton")
      },
      viewsManagerWaitingBar: {
        container: document.getElementById("viewsManagerStatusWaiting"),
        closeButton: document.getElementById("viewsManagerStatusWaitingCloseButton"),
        label: document.getElementById("viewsManagerStatusWaitingLabel")
      },
      manageMenu: {
        button: document.getElementById("viewsManagerStatusActionButton"),
        menu: document.getElementById("viewsManagerStatusActionOptions"),
        copy: document.getElementById("viewsManagerStatusActionCopy"),
        cut: document.getElementById("viewsManagerStatusActionCut"),
        delete: document.getElementById("viewsManagerStatusActionDelete"),
        exportSelected: document.getElementById("viewsManagerStatusActionExport")
      }
    },
    findBar: {
      bar: document.getElementById("findbar"),
      toggleButton: document.getElementById("viewFindButton"),
      findField: document.getElementById("findInput"),
      highlightAllCheckbox: document.getElementById("findHighlightAll"),
      caseSensitiveCheckbox: document.getElementById("findMatchCase"),
      matchDiacriticsCheckbox: document.getElementById("findMatchDiacritics"),
      entireWordCheckbox: document.getElementById("findEntireWord"),
      findMsg: document.getElementById("findMsg"),
      findResultsCount: document.getElementById("findResultsCount"),
      findPreviousButton: document.getElementById("findPreviousButton"),
      findNextButton: document.getElementById("findNextButton")
    },
    passwordOverlay: {
      dialog: document.getElementById("passwordDialog"),
      label: document.getElementById("passwordText"),
      input: document.getElementById("password"),
      submitButton: document.getElementById("passwordSubmit"),
      cancelButton: document.getElementById("passwordCancel")
    },
    documentProperties: {
      dialog: document.getElementById("documentPropertiesDialog"),
      closeButton: document.getElementById("documentPropertiesClose"),
      fields: {
        fileName: document.getElementById("fileNameField"),
        fileSize: document.getElementById("fileSizeField"),
        title: document.getElementById("titleField"),
        author: document.getElementById("authorField"),
        subject: document.getElementById("subjectField"),
        keywords: document.getElementById("keywordsField"),
        creationDate: document.getElementById("creationDateField"),
        modificationDate: document.getElementById("modificationDateField"),
        creator: document.getElementById("creatorField"),
        producer: document.getElementById("producerField"),
        version: document.getElementById("versionField"),
        pageCount: document.getElementById("pageCountField"),
        pageSize: document.getElementById("pageSizeField"),
        linearized: document.getElementById("linearizedField")
      }
    },
    altTextDialog: {
      dialog: document.getElementById("altTextDialog"),
      optionDescription: document.getElementById("descriptionButton"),
      optionDecorative: document.getElementById("decorativeButton"),
      textarea: document.getElementById("descriptionTextarea"),
      cancelButton: document.getElementById("altTextCancel"),
      saveButton: document.getElementById("altTextSave")
    },
    newAltTextDialog: {
      dialog: document.getElementById("newAltTextDialog"),
      title: document.getElementById("newAltTextTitle"),
      descriptionContainer: document.getElementById("newAltTextDescriptionContainer"),
      textarea: document.getElementById("newAltTextDescriptionTextarea"),
      disclaimer: document.getElementById("newAltTextDisclaimer"),
      learnMore: document.getElementById("newAltTextLearnMore"),
      imagePreview: document.getElementById("newAltTextImagePreview"),
      createAutomatically: document.getElementById("newAltTextCreateAutomatically"),
      createAutomaticallyButton: document.getElementById("newAltTextCreateAutomaticallyButton"),
      downloadModel: document.getElementById("newAltTextDownloadModel"),
      downloadModelDescription: document.getElementById("newAltTextDownloadModelDescription"),
      error: document.getElementById("newAltTextError"),
      errorCloseButton: document.getElementById("newAltTextCloseButton"),
      cancelButton: document.getElementById("newAltTextCancel"),
      notNowButton: document.getElementById("newAltTextNotNow"),
      saveButton: document.getElementById("newAltTextSave")
    },
    altTextSettingsDialog: {
      dialog: document.getElementById("altTextSettingsDialog"),
      createModelButton: document.getElementById("createModelButton"),
      learnMore: document.getElementById("altTextSettingsLearnMore"),
      showAltTextDialogButton: document.getElementById("showAltTextDialogButton"),
      altTextSettingsCloseButton: document.getElementById("altTextSettingsCloseButton"),
      closeButton: document.getElementById("altTextSettingsCloseButton")
    },
    addSignatureDialog: {
      dialog: document.getElementById("addSignatureDialog"),
      panels: document.getElementById("addSignatureActionContainer"),
      typeButton: document.getElementById("addSignatureTypeButton"),
      typeInput: document.getElementById("addSignatureTypeInput"),
      drawButton: document.getElementById("addSignatureDrawButton"),
      drawSVG: document.getElementById("addSignatureDraw"),
      drawPlaceholder: document.getElementById("addSignatureDrawPlaceholder"),
      drawThickness: document.getElementById("addSignatureDrawThickness"),
      imageButton: document.getElementById("addSignatureImageButton"),
      imageSVG: document.getElementById("addSignatureImage"),
      imagePlaceholder: document.getElementById("addSignatureImagePlaceholder"),
      imagePicker: document.getElementById("addSignatureFilePicker"),
      imagePickerLink: document.getElementById("addSignatureImageBrowse"),
      description: document.getElementById("addSignatureDescription"),
      clearButton: document.getElementById("clearSignatureButton"),
      saveContainer: document.getElementById("addSignatureSaveContainer"),
      saveCheckbox: document.getElementById("addSignatureSaveCheckbox"),
      errorBar: document.getElementById("addSignatureError"),
      errorTitle: document.getElementById("addSignatureErrorTitle"),
      errorDescription: document.getElementById("addSignatureErrorDescription"),
      errorCloseButton: document.getElementById("addSignatureErrorCloseButton"),
      cancelButton: document.getElementById("addSignatureCancelButton"),
      addButton: document.getElementById("addSignatureAddButton")
    },
    editSignatureDialog: {
      dialog: document.getElementById("editSignatureDescriptionDialog"),
      description: document.getElementById("editSignatureDescription"),
      editSignatureView: document.getElementById("editSignatureView"),
      cancelButton: document.getElementById("editSignatureCancelButton"),
      updateButton: document.getElementById("editSignatureUpdateButton")
    },
    annotationEditorParams: {
      editorCommentsSidebar: document.getElementById("editorCommentsSidebar"),
      editorCommentsSidebarCount: document.getElementById("editorCommentsSidebarCount"),
      editorCommentsSidebarTitle: document.getElementById("editorCommentsSidebarTitle"),
      editorCommentsSidebarCloseButton: document.getElementById("editorCommentsSidebarCloseButton"),
      editorCommentsSidebarList: document.getElementById("editorCommentsSidebarList"),
      editorCommentsSidebarResizer: document.getElementById("editorCommentsSidebarResizer"),
      editorFreeTextFontSize: document.getElementById("editorFreeTextFontSize"),
      editorFreeTextColor: document.getElementById("editorFreeTextColor"),
      editorInkColor: document.getElementById("editorInkColor"),
      editorInkThickness: document.getElementById("editorInkThickness"),
      editorInkOpacity: document.getElementById("editorInkOpacity"),
      editorStampAddImage: document.getElementById("editorStampAddImage"),
      editorSignatureAddSignature: document.getElementById("editorSignatureAddSignature"),
      editorFreeHighlightThickness: document.getElementById("editorFreeHighlightThickness"),
      editorHighlightShowAll: document.getElementById("editorHighlightShowAll")
    },
    printContainer: document.getElementById("printContainer"),
    editorUndoBar: {
      container: document.getElementById("editorUndoBar"),
      message: document.getElementById("editorUndoBarMessage"),
      undoButton: document.getElementById("editorUndoBarUndoButton"),
      closeButton: document.getElementById("editorUndoBarCloseButton")
    },
    ...{},
    editCommentDialog: {
      dialog: document.getElementById("commentManagerDialog"),
      toolbar: document.getElementById("commentManagerToolbar"),
      title: document.getElementById("commentManagerTitle"),
      textInput: document.getElementById("commentManagerTextInput"),
      cancelButton: document.getElementById("commentManagerCancelButton"),
      saveButton: document.getElementById("commentManagerSaveButton")
    }
  };
}
function webViewerLoad() {
  const config = getViewerConfiguration();
  const event = new CustomEvent("webviewerloaded", {
    bubbles: true,
    cancelable: true,
    detail: {
      source: window
    }
  });
  try {
    parent.document.dispatchEvent(event);
  } catch (ex) {
    console.error("webviewerloaded:", ex);
    document.dispatchEvent(event);
  }
  PDFViewerApplication.run(config);
}
document.blockUnblockOnload?.(true);
if (document.readyState === "interactive" || document.readyState === "complete") {
  webViewerLoad();
} else {
  document.addEventListener("DOMContentLoaded", webViewerLoad, true);
}

export { PDFViewerApplication, AppConstants as PDFViewerApplicationConstants, AppOptions as PDFViewerApplicationOptions };

//# sourceMappingURL=viewer.mjs.map