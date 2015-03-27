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
/* globals PDFJS, PDFBug, FirefoxCom, Stats, Cache, ProgressBar,
           DownloadManager, getFileName, scrollIntoView, getPDFFileNameFromURL,
           PDFHistory, Preferences, SidebarView, ViewHistory, PageView,
           PDFThumbnailViewer, URL, noContextMenuHandler, SecondaryToolbar,
           PasswordPrompt, PresentationMode, HandTool, Promise,
           DocumentProperties, DocumentOutlineView, DocumentAttachmentsView,
           OverlayManager, PDFFindController, PDFFindBar, getVisibleElements,
           watchScroll, PDFViewer, PDFRenderingQueue, PresentationModeState,
           RenderingStates, DEFAULT_SCALE, UNKNOWN_SCALE,
           IGNORE_CURRENT_POSITION_ON_ZOOM: true */

'use strict';

var DEFAULT_URL = 'compressed.tracemonkey-pldi-09.pdf';
var DEFAULT_SCALE_DELTA = 1.1;
var MIN_SCALE = 0.25;
var MAX_SCALE = 10.0;
var VIEW_HISTORY_MEMORY = 20;
var SCALE_SELECT_CONTAINER_PADDING = 8;
var SCALE_SELECT_PADDING = 22;
var PAGE_NUMBER_LOADING_INDICATOR = 'visiblePageIsLoading';
var DISABLE_AUTO_FETCH_LOADING_BAR_TIMEOUT = 5000;

PDFJS.imageResourcesPath = './images/';
  PDFJS.workerSrc = '../build/pdf.worker.js';
  PDFJS.cMapUrl = '../web/cmaps/';
  PDFJS.cMapPacked = true;

var mozL10n = document.mozL10n || document.webL10n;


var CSS_UNITS = 96.0 / 72.0;
var DEFAULT_SCALE = 'auto';
var UNKNOWN_SCALE = 0;
var MAX_AUTO_SCALE = 1.25;
var SCROLLBAR_PADDING = 40;
var VERTICAL_PADDING = 5;
var DEFAULT_CACHE_SIZE = 10;

// optimised CSS custom property getter/setter
var CustomStyle = (function CustomStyleClosure() {

  // As noted on: http://www.zachstronaut.com/posts/2009/02/17/
  //              animate-css-transforms-firefox-webkit.html
  // in some versions of IE9 it is critical that ms appear in this list
  // before Moz
  var prefixes = ['ms', 'Moz', 'Webkit', 'O'];
  var _cache = {};

  function CustomStyle() {}

  CustomStyle.getProp = function get(propName, element) {
    // check cache only when no element is given
    if (arguments.length === 1 && typeof _cache[propName] === 'string') {
      return _cache[propName];
    }

    element = element || document.documentElement;
    var style = element.style, prefixed, uPropName;

    // test standard property first
    if (typeof style[propName] === 'string') {
      return (_cache[propName] = propName);
    }

    // capitalize
    uPropName = propName.charAt(0).toUpperCase() + propName.slice(1);

    // test vendor specific properties
    for (var i = 0, l = prefixes.length; i < l; i++) {
      prefixed = prefixes[i] + uPropName;
      if (typeof style[prefixed] === 'string') {
        return (_cache[propName] = prefixed);
      }
    }

    //if all fails then set to undefined
    return (_cache[propName] = 'undefined');
  };

  CustomStyle.setProp = function set(propName, element, str) {
    var prop = this.getProp(propName);
    if (prop !== 'undefined') {
      element.style[prop] = str;
    }
  };

  return CustomStyle;
})();

function getFileName(url) {
  var anchor = url.indexOf('#');
  var query = url.indexOf('?');
  var end = Math.min(
    anchor > 0 ? anchor : url.length,
    query > 0 ? query : url.length);
  return url.substring(url.lastIndexOf('/', end) + 1, end);
}

/**
 * Returns scale factor for the canvas. It makes sense for the HiDPI displays.
 * @return {Object} The object with horizontal (sx) and vertical (sy)
                    scales. The scaled property is set to false if scaling is
                    not required, true otherwise.
 */
function getOutputScale(ctx) {
  var devicePixelRatio = window.devicePixelRatio || 1;
  var backingStoreRatio = ctx.webkitBackingStorePixelRatio ||
                          ctx.mozBackingStorePixelRatio ||
                          ctx.msBackingStorePixelRatio ||
                          ctx.oBackingStorePixelRatio ||
                          ctx.backingStorePixelRatio || 1;
  var pixelRatio = devicePixelRatio / backingStoreRatio;
  return {
    sx: pixelRatio,
    sy: pixelRatio,
    scaled: pixelRatio !== 1
  };
}

/**
 * Scrolls specified element into view of its parent.
 * element {Object} The element to be visible.
 * spot {Object} An object with optional top and left properties,
 *               specifying the offset from the top left edge.
 */
function scrollIntoView(element, spot) {
  // Assuming offsetParent is available (it's not available when viewer is in
  // hidden iframe or object). We have to scroll: if the offsetParent is not set
  // producing the error. See also animationStartedClosure.
  var parent = element.offsetParent;
  var offsetY = element.offsetTop + element.clientTop;
  var offsetX = element.offsetLeft + element.clientLeft;
  if (!parent) {
    console.error('offsetParent is not set -- cannot scroll');
    return;
  }
  while (parent.clientHeight === parent.scrollHeight) {
    if (parent.dataset._scaleY) {
      offsetY /= parent.dataset._scaleY;
      offsetX /= parent.dataset._scaleX;
    }
    offsetY += parent.offsetTop;
    offsetX += parent.offsetLeft;
    parent = parent.offsetParent;
    if (!parent) {
      return; // no need to scroll
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

/**
 * Helper function to start monitoring the scroll event and converting them into
 * PDF.js friendly one: with scroll debounce and scroll direction.
 */
function watchScroll(viewAreaElement, callback) {
  var debounceScroll = function debounceScroll(evt) {
    if (rAF) {
      return;
    }
    // schedule an invocation of scroll for next animation frame.
    rAF = window.requestAnimationFrame(function viewAreaElementScrolled() {
      rAF = null;

      var currentY = viewAreaElement.scrollTop;
      var lastY = state.lastY;
      if (currentY > lastY) {
        state.down = true;
      } else if (currentY < lastY) {
        state.down = false;
      }
      state.lastY = currentY;
      // else do nothing and use previous value
      callback(state);
    });
  };

  var state = {
    down: true,
    lastY: viewAreaElement.scrollTop,
    _eventHandler: debounceScroll
  };

  var rAF = null;
  viewAreaElement.addEventListener('scroll', debounceScroll, true);
  return state;
}

/**
 * Generic helper to find out what elements are visible within a scroll pane.
 */
function getVisibleElements(scrollEl, views, sortByVisibility) {
  var top = scrollEl.scrollTop, bottom = top + scrollEl.clientHeight;
  var left = scrollEl.scrollLeft, right = left + scrollEl.clientWidth;

  var visible = [], view;
  var currentHeight, viewHeight, hiddenHeight, percentHeight;
  var currentWidth, viewWidth;
  for (var i = 0, ii = views.length; i < ii; ++i) {
    view = views[i];
    currentHeight = view.el.offsetTop + view.el.clientTop;
    viewHeight = view.el.clientHeight;
    if ((currentHeight + viewHeight) < top) {
      continue;
    }
    if (currentHeight > bottom) {
      break;
    }
    currentWidth = view.el.offsetLeft + view.el.clientLeft;
    viewWidth = view.el.clientWidth;
    if ((currentWidth + viewWidth) < left || currentWidth > right) {
      continue;
    }
    hiddenHeight = Math.max(0, top - currentHeight) +
      Math.max(0, currentHeight + viewHeight - bottom);
    percentHeight = ((viewHeight - hiddenHeight) * 100 / viewHeight) | 0;

    visible.push({ id: view.id, x: currentWidth, y: currentHeight,
      view: view, percent: percentHeight });
  }

  var first = visible[0];
  var last = visible[visible.length - 1];

  if (sortByVisibility) {
    visible.sort(function(a, b) {
      var pc = a.percent - b.percent;
      if (Math.abs(pc) > 0.001) {
        return -pc;
      }
      return a.id - b.id; // ensure stability
    });
  }
  return {first: first, last: last, views: visible};
}

/**
 * Event handler to suppress context menu.
 */
function noContextMenuHandler(e) {
  e.preventDefault();
}

/**
 * Returns the filename or guessed filename from the url (see issue 3455).
 * url {String} The original PDF location.
 * @return {String} Guessed PDF file name.
 */
function getPDFFileNameFromURL(url) {
  var reURI = /^(?:([^:]+:)?\/\/[^\/]+)?([^?#]*)(\?[^#]*)?(#.*)?$/;
  //            SCHEME      HOST         1.PATH  2.QUERY   3.REF
  // Pattern to get last matching NAME.pdf
  var reFilename = /[^\/?#=]+\.pdf\b(?!.*\.pdf\b)/i;
  var splitURI = reURI.exec(url);
  var suggestedFilename = reFilename.exec(splitURI[1]) ||
                           reFilename.exec(splitURI[2]) ||
                           reFilename.exec(splitURI[3]);
  if (suggestedFilename) {
    suggestedFilename = suggestedFilename[0];
    if (suggestedFilename.indexOf('%') !== -1) {
      // URL-encoded %2Fpath%2Fto%2Ffile.pdf should be file.pdf
      try {
        suggestedFilename =
          reFilename.exec(decodeURIComponent(suggestedFilename))[0];
      } catch(e) { // Possible (extremely rare) errors:
        // URIError "Malformed URI", e.g. for "%AA.pdf"
        // TypeError "null has no properties", e.g. for "%2F.pdf"
      }
    }
  }
  return suggestedFilename || 'document.pdf';
}

var ProgressBar = (function ProgressBarClosure() {

  function clamp(v, min, max) {
    return Math.min(Math.max(v, min), max);
  }

  function ProgressBar(id, opts) {
    this.visible = true;

    // Fetch the sub-elements for later.
    this.div = document.querySelector(id + ' .progress');

    // Get the loading bar element, so it can be resized to fit the viewer.
    this.bar = this.div.parentNode;

    // Get options, with sensible defaults.
    this.height = opts.height || 100;
    this.width = opts.width || 100;
    this.units = opts.units || '%';

    // Initialize heights.
    this.div.style.height = this.height + this.units;
    this.percent = 0;
  }

  ProgressBar.prototype = {

    updateBar: function ProgressBar_updateBar() {
      if (this._indeterminate) {
        this.div.classList.add('indeterminate');
        this.div.style.width = this.width + this.units;
        return;
      }

      this.div.classList.remove('indeterminate');
      var progressSize = this.width * this._percent / 100;
      this.div.style.width = progressSize + this.units;
    },

    get percent() {
      return this._percent;
    },

    set percent(val) {
      this._indeterminate = isNaN(val);
      this._percent = clamp(val, 0, 100);
      this.updateBar();
    },

    setWidth: function ProgressBar_setWidth(viewer) {
      if (viewer) {
        var container = viewer.parentNode;
        var scrollbarWidth = container.offsetWidth - viewer.offsetWidth;
        if (scrollbarWidth > 0) {
          this.bar.setAttribute('style', 'width: calc(100% - ' +
                                         scrollbarWidth + 'px);');
        }
      }
    },

    hide: function ProgressBar_hide() {
      if (!this.visible) {
        return;
      }
      this.visible = false;
      this.bar.classList.add('hidden');
      document.body.classList.remove('loadingInProgress');
    },

    show: function ProgressBar_show() {
      if (this.visible) {
        return;
      }
      this.visible = true;
      document.body.classList.add('loadingInProgress');
      this.bar.classList.remove('hidden');
    }
  };

  return ProgressBar;
})();

var Cache = function cacheCache(size) {
  var data = [];
  this.push = function cachePush(view) {
    var i = data.indexOf(view);
    if (i >= 0) {
      data.splice(i, 1);
    }
    data.push(view);
    if (data.length > size) {
      data.shift().destroy();
    }
  };
  this.resize = function (newSize) {
    size = newSize;
    while (data.length > size) {
      data.shift().destroy();
    }
  };
};



var DEFAULT_PREFERENCES = {
  showPreviousViewOnLoad: true,
  defaultZoomValue: '',
  sidebarViewOnLoad: 0,
  enableHandToolOnLoad: false,
  enableWebGL: false,
  pdfBugEnabled: false,
  disableRange: false,
  disableStream: false,
  disableAutoFetch: false,
  disableFontFace: false,
  disableTextLayer: false,
  useOnlyCssZoom: false
};


var SidebarView = {
  NONE: 0,
  THUMBS: 1,
  OUTLINE: 2,
  ATTACHMENTS: 3
};

/**
 * Preferences - Utility for storing persistent settings.
 *   Used for settings that should be applied to all opened documents,
 *   or every time the viewer is loaded.
 */
var Preferences = {
  prefs: Object.create(DEFAULT_PREFERENCES),
  isInitializedPromiseResolved: false,
  initializedPromise: null,

  /**
   * Initialize and fetch the current preference values from storage.
   * @return {Promise} A promise that is resolved when the preferences
   *                   have been initialized.
   */
  initialize: function preferencesInitialize() {
    return this.initializedPromise =
        this._readFromStorage(DEFAULT_PREFERENCES).then(function(prefObj) {
      this.isInitializedPromiseResolved = true;
      if (prefObj) {
        this.prefs = prefObj;
      }
    }.bind(this));
  },

  /**
   * Stub function for writing preferences to storage.
   * NOTE: This should be overridden by a build-specific function defined below.
   * @param {Object} prefObj The preferences that should be written to storage.
   * @return {Promise} A promise that is resolved when the preference values
   *                   have been written.
   */
  _writeToStorage: function preferences_writeToStorage(prefObj) {
    return Promise.resolve();
  },

  /**
   * Stub function for reading preferences from storage.
   * NOTE: This should be overridden by a build-specific function defined below.
   * @param {Object} prefObj The preferences that should be read from storage.
   * @return {Promise} A promise that is resolved with an {Object} containing
   *                   the preferences that have been read.
   */
  _readFromStorage: function preferences_readFromStorage(prefObj) {
    return Promise.resolve();
  },

  /**
   * Reset the preferences to their default values and update storage.
   * @return {Promise} A promise that is resolved when the preference values
   *                   have been reset.
   */
  reset: function preferencesReset() {
    return this.initializedPromise.then(function() {
      this.prefs = Object.create(DEFAULT_PREFERENCES);
      return this._writeToStorage(DEFAULT_PREFERENCES);
    }.bind(this));
  },

  /**
   * Replace the current preference values with the ones from storage.
   * @return {Promise} A promise that is resolved when the preference values
   *                   have been updated.
   */
  reload: function preferencesReload() {
    return this.initializedPromise.then(function () {
      this._readFromStorage(DEFAULT_PREFERENCES).then(function(prefObj) {
        if (prefObj) {
          this.prefs = prefObj;
        }
      }.bind(this));
    }.bind(this));
  },

  /**
   * Set the value of a preference.
   * @param {string} name The name of the preference that should be changed.
   * @param {boolean|number|string} value The new value of the preference.
   * @return {Promise} A promise that is resolved when the value has been set,
   *                   provided that the preference exists and the types match.
   */
  set: function preferencesSet(name, value) {
    return this.initializedPromise.then(function () {
      if (DEFAULT_PREFERENCES[name] === undefined) {
        throw new Error('preferencesSet: \'' + name + '\' is undefined.');
      } else if (value === undefined) {
        throw new Error('preferencesSet: no value is specified.');
      }
      var valueType = typeof value;
      var defaultType = typeof DEFAULT_PREFERENCES[name];

      if (valueType !== defaultType) {
        if (valueType === 'number' && defaultType === 'string') {
          value = value.toString();
        } else {
          throw new Error('Preferences_set: \'' + value + '\' is a \"' +
                          valueType + '\", expected \"' + defaultType + '\".');
        }
      } else {
        if (valueType === 'number' && (value | 0) !== value) {
          throw new Error('Preferences_set: \'' + value +
                          '\' must be an \"integer\".');
        }
      }
      this.prefs[name] = value;
      return this._writeToStorage(this.prefs);
    }.bind(this));
  },

  /**
   * Get the value of a preference.
   * @param {string} name The name of the preference whose value is requested.
   * @return {Promise} A promise that is resolved with a {boolean|number|string}
   *                   containing the value of the preference.
   */
  get: function preferencesGet(name) {
    return this.initializedPromise.then(function () {
      var defaultValue = DEFAULT_PREFERENCES[name];

      if (defaultValue === undefined) {
        throw new Error('preferencesGet: \'' + name + '\' is undefined.');
      } else {
        var prefValue = this.prefs[name];

        if (prefValue !== undefined) {
          return prefValue;
        }
      }
      return defaultValue;
    }.bind(this));
  }
};



Preferences._writeToStorage = function (prefObj) {
  return new Promise(function (resolve) {
    localStorage.setItem('pdfjs.preferences', JSON.stringify(prefObj));
    resolve();
  });
};

Preferences._readFromStorage = function (prefObj) {
  return new Promise(function (resolve) {
    var readPrefs = JSON.parse(localStorage.getItem('pdfjs.preferences'));
    resolve(readPrefs);
  });
};


(function mozPrintCallbackPolyfillClosure() {
  if ('mozPrintCallback' in document.createElement('canvas')) {
    return;
  }
  // Cause positive result on feature-detection:
  HTMLCanvasElement.prototype.mozPrintCallback = undefined;

  var canvases;   // During print task: non-live NodeList of <canvas> elements
  var index;      // Index of <canvas> element that is being processed

  var print = window.print;
  window.print = function print() {
    if (canvases) {
      console.warn('Ignored window.print() because of a pending print job.');
      return;
    }
    try {
      dispatchEvent('beforeprint');
    } finally {
      canvases = document.querySelectorAll('canvas');
      index = -1;
      next();
    }
  };

  function dispatchEvent(eventType) {
    var event = document.createEvent('CustomEvent');
    event.initCustomEvent(eventType, false, false, 'custom');
    window.dispatchEvent(event);
  }

  function next() {
    if (!canvases) {
      return; // Print task cancelled by user (state reset in abort())
    }

    renderProgress();
    if (++index < canvases.length) {
      var canvas = canvases[index];
      if (typeof canvas.mozPrintCallback === 'function') {
        canvas.mozPrintCallback({
          context: canvas.getContext('2d'),
          abort: abort,
          done: next
        });
      } else {
        next();
      }
    } else {
      renderProgress();
      print.call(window);
      setTimeout(abort, 20); // Tidy-up
    }
  }

  function abort() {
    if (canvases) {
      canvases = null;
      renderProgress();
      dispatchEvent('afterprint');
    }
  }

  function renderProgress() {
    var progressContainer = document.getElementById('mozPrintCallback-shim');
    if (canvases) {
      var progress = Math.round(100 * index / canvases.length);
      var progressBar = progressContainer.querySelector('progress');
      var progressPerc = progressContainer.querySelector('.relative-progress');
      progressBar.value = progress;
      progressPerc.textContent = progress + '%';
      progressContainer.removeAttribute('hidden');
      progressContainer.onclick = abort;
    } else {
      progressContainer.setAttribute('hidden', '');
    }
  }

  var hasAttachEvent = !!document.attachEvent;

  window.addEventListener('keydown', function(event) {
    // Intercept Cmd/Ctrl + P in all browsers.
    // Also intercept Cmd/Ctrl + Shift + P in Chrome and Opera
    if (event.keyCode === 80/*P*/ && (event.ctrlKey || event.metaKey) &&
        !event.altKey && (!event.shiftKey || window.chrome || window.opera)) {
      window.print();
      if (hasAttachEvent) {
        // Only attachEvent can cancel Ctrl + P dialog in IE <=10
        // attachEvent is gone in IE11, so the dialog will re-appear in IE11.
        return;
      }
      event.preventDefault();
      if (event.stopImmediatePropagation) {
        event.stopImmediatePropagation();
      } else {
        event.stopPropagation();
      }
      return;
    }
    if (event.keyCode === 27 && canvases) { // Esc
      abort();
    }
  }, true);
  if (hasAttachEvent) {
    document.attachEvent('onkeydown', function(event) {
      event = event || window.event;
      if (event.keyCode === 80/*P*/ && event.ctrlKey) {
        event.keyCode = 0;
        return false;
      }
    });
  }

  if ('onbeforeprint' in window) {
    // Do not propagate before/afterprint events when they are not triggered
    // from within this polyfill. (FF/IE).
    var stopPropagationIfNeeded = function(event) {
      if (event.detail !== 'custom' && event.stopImmediatePropagation) {
        event.stopImmediatePropagation();
      }
    };
    window.addEventListener('beforeprint', stopPropagationIfNeeded, false);
    window.addEventListener('afterprint', stopPropagationIfNeeded, false);
  }
})();



var DownloadManager = (function DownloadManagerClosure() {

  function download(blobUrl, filename) {
    var a = document.createElement('a');
    if (a.click) {
      // Use a.click() if available. Otherwise, Chrome might show
      // "Unsafe JavaScript attempt to initiate a navigation change
      //  for frame with URL" and not open the PDF at all.
      // Supported by (not mentioned = untested):
      // - Firefox 6 - 19 (4- does not support a.click, 5 ignores a.click)
      // - Chrome 19 - 26 (18- does not support a.click)
      // - Opera 9 - 12.15
      // - Internet Explorer 6 - 10
      // - Safari 6 (5.1- does not support a.click)
      a.href = blobUrl;
      a.target = '_parent';
      // Use a.download if available. This increases the likelihood that
      // the file is downloaded instead of opened by another PDF plugin.
      if ('download' in a) {
        a.download = filename;
      }
      // <a> must be in the document for IE and recent Firefox versions.
      // (otherwise .click() is ignored)
      (document.body || document.documentElement).appendChild(a);
      a.click();
      a.parentNode.removeChild(a);
    } else {
      if (window.top === window &&
          blobUrl.split('#')[0] === window.location.href.split('#')[0]) {
        // If _parent == self, then opening an identical URL with different
        // location hash will only cause a navigation, not a download.
        var padCharacter = blobUrl.indexOf('?') === -1 ? '?' : '&';
        blobUrl = blobUrl.replace(/#|$/, padCharacter + '$&');
      }
      window.open(blobUrl, '_parent');
    }
  }

  function DownloadManager() {}

  DownloadManager.prototype = {
    downloadUrl: function DownloadManager_downloadUrl(url, filename) {
      if (!PDFJS.isValidUrl(url, true)) {
        return; // restricted/invalid URL
      }

      download(url + '#pdfjs.action=download', filename);
    },

    downloadData: function DownloadManager_downloadData(data, filename,
                                                        contentType) {
      if (navigator.msSaveBlob) { // IE10 and above
        return navigator.msSaveBlob(new Blob([data], { type: contentType }),
                                    filename);
      }

      var blobUrl = PDFJS.createObjectURL(data, contentType);
      download(blobUrl, filename);
    },

    download: function DownloadManager_download(blob, url, filename) {
      if (!URL) {
        // URL.createObjectURL is not supported
        this.downloadUrl(url, filename);
        return;
      }

      if (navigator.msSaveBlob) {
        // IE10 / IE11
        if (!navigator.msSaveBlob(blob, filename)) {
          this.downloadUrl(url, filename);
        }
        return;
      }

      var blobUrl = URL.createObjectURL(blob);
      download(blobUrl, filename);
    }
  };

  return DownloadManager;
})();





/**
 * View History - This is a utility for saving various view parameters for
 *                recently opened files.
 *
 * The way that the view parameters are stored depends on how PDF.js is built,
 * for 'node make <flag>' the following cases exist:
 *  - FIREFOX or MOZCENTRAL - uses sessionStorage.
 *  - B2G                   - uses asyncStorage.
 *  - GENERIC or CHROME     - uses localStorage, if it is available.
 */
var ViewHistory = (function ViewHistoryClosure() {
  function ViewHistory(fingerprint) {
    this.fingerprint = fingerprint;
    this.isInitializedPromiseResolved = false;
    this.initializedPromise =
        this._readFromStorage().then(function (databaseStr) {
      this.isInitializedPromiseResolved = true;

      var database = JSON.parse(databaseStr || '{}');
      if (!('files' in database)) {
        database.files = [];
      }
      if (database.files.length >= VIEW_HISTORY_MEMORY) {
        database.files.shift();
      }
      var index;
      for (var i = 0, length = database.files.length; i < length; i++) {
        var branch = database.files[i];
        if (branch.fingerprint === this.fingerprint) {
          index = i;
          break;
        }
      }
      if (typeof index !== 'number') {
        index = database.files.push({fingerprint: this.fingerprint}) - 1;
      }
      this.file = database.files[index];
      this.database = database;
    }.bind(this));
  }

  ViewHistory.prototype = {
    _writeToStorage: function ViewHistory_writeToStorage() {
      return new Promise(function (resolve) {
        var databaseStr = JSON.stringify(this.database);



        localStorage.setItem('database', databaseStr);
        resolve();
      }.bind(this));
    },

    _readFromStorage: function ViewHistory_readFromStorage() {
      return new Promise(function (resolve) {


        resolve(localStorage.getItem('database'));
      });
    },

    set: function ViewHistory_set(name, val) {
      if (!this.isInitializedPromiseResolved) {
        return;
      }
      this.file[name] = val;
      return this._writeToStorage();
    },

    setMultiple: function ViewHistory_setMultiple(properties) {
      if (!this.isInitializedPromiseResolved) {
        return;
      }
      for (var name in properties) {
        this.file[name] = properties[name];
      }
      return this._writeToStorage();
    },

    get: function ViewHistory_get(name, defaultValue) {
      if (!this.isInitializedPromiseResolved) {
        return defaultValue;
      }
      return this.file[name] || defaultValue;
    }
  };

  return ViewHistory;
})();


/**
 * Creates a "search bar" given a set of DOM elements that act as controls
 * for searching or for setting search preferences in the UI. This object
 * also sets up the appropriate events for the controls. Actual searching
 * is done by PDFFindController.
 */
var PDFFindBar = (function PDFFindBarClosure() {
  function PDFFindBar(options) {
    this.opened = false;
    this.bar = options.bar || null;
    this.toggleButton = options.toggleButton || null;
    this.findField = options.findField || null;
    this.highlightAll = options.highlightAllCheckbox || null;
    this.caseSensitive = options.caseSensitiveCheckbox || null;
    this.findMsg = options.findMsg || null;
    this.findStatusIcon = options.findStatusIcon || null;
    this.findPreviousButton = options.findPreviousButton || null;
    this.findNextButton = options.findNextButton || null;
    this.findController = options.findController || null;

    if (this.findController === null) {
      throw new Error('PDFFindBar cannot be used without a ' +
                      'PDFFindController instance.');
    }

    // Add event listeners to the DOM elements.
    var self = this;
    this.toggleButton.addEventListener('click', function() {
      self.toggle();
    });

    this.findField.addEventListener('input', function() {
      self.dispatchEvent('');
    });

    this.bar.addEventListener('keydown', function(evt) {
      switch (evt.keyCode) {
        case 13: // Enter
          if (evt.target === self.findField) {
            self.dispatchEvent('again', evt.shiftKey);
          }
          break;
        case 27: // Escape
          self.close();
          break;
      }
    });

    this.findPreviousButton.addEventListener('click', function() {
      self.dispatchEvent('again', true);
    });

    this.findNextButton.addEventListener('click', function() {
      self.dispatchEvent('again', false);
    });

    this.highlightAll.addEventListener('click', function() {
      self.dispatchEvent('highlightallchange');
    });

    this.caseSensitive.addEventListener('click', function() {
      self.dispatchEvent('casesensitivitychange');
    });
  }

  PDFFindBar.prototype = {
    dispatchEvent: function PDFFindBar_dispatchEvent(type, findPrev) {
      var event = document.createEvent('CustomEvent');
      event.initCustomEvent('find' + type, true, true, {
        query: this.findField.value,
        caseSensitive: this.caseSensitive.checked,
        highlightAll: this.highlightAll.checked,
        findPrevious: findPrev
      });
      return window.dispatchEvent(event);
    },

    updateUIState: function PDFFindBar_updateUIState(state, previous) {
      var notFound = false;
      var findMsg = '';
      var status = '';

      switch (state) {
        case FindStates.FIND_FOUND:
          break;

        case FindStates.FIND_PENDING:
          status = 'pending';
          break;

        case FindStates.FIND_NOTFOUND:
          findMsg = mozL10n.get('find_not_found', null, 'Phrase not found');
          notFound = true;
          break;

        case FindStates.FIND_WRAPPED:
          if (previous) {
            findMsg = mozL10n.get('find_reached_top', null,
              'Reached top of document, continued from bottom');
          } else {
            findMsg = mozL10n.get('find_reached_bottom', null,
              'Reached end of document, continued from top');
          }
          break;
      }

      if (notFound) {
        this.findField.classList.add('notFound');
      } else {
        this.findField.classList.remove('notFound');
      }

      this.findField.setAttribute('data-status', status);
      this.findMsg.textContent = findMsg;
    },

    open: function PDFFindBar_open() {
      if (!this.opened) {
        this.opened = true;
        this.toggleButton.classList.add('toggled');
        this.bar.classList.remove('hidden');
      }
      this.findField.select();
      this.findField.focus();
    },

    close: function PDFFindBar_close() {
      if (!this.opened) {
        return;
      }
      this.opened = false;
      this.toggleButton.classList.remove('toggled');
      this.bar.classList.add('hidden');
      this.findController.active = false;
    },

    toggle: function PDFFindBar_toggle() {
      if (this.opened) {
        this.close();
      } else {
        this.open();
      }
    }
  };
  return PDFFindBar;
})();



var FindStates = {
  FIND_FOUND: 0,
  FIND_NOTFOUND: 1,
  FIND_WRAPPED: 2,
  FIND_PENDING: 3
};

/**
 * Provides "search" or "find" functionality for the PDF.
 * This object actually performs the search for a given string.
 */
var PDFFindController = (function PDFFindControllerClosure() {
  function PDFFindController(options) {
    this.startedTextExtraction = false;
    this.extractTextPromises = [];
    this.pendingFindMatches = {};
    this.active = false; // If active, find results will be highlighted.
    this.pageContents = []; // Stores the text for each page.
    this.pageMatches = [];
    this.selected = { // Currently selected match.
      pageIdx: -1,
      matchIdx: -1
    };
    this.offset = { // Where the find algorithm currently is in the document.
      pageIdx: null,
      matchIdx: null
    };
    this.pagesToSearch = null;
    this.resumePageIdx = null;
    this.state = null;
    this.dirtyMatch = false;
    this.findTimeout = null;
    this.pdfViewer = options.pdfViewer || null;
    this.integratedFind = options.integratedFind || false;
    this.charactersToNormalize = {
      '\u2018': '\'', // Left single quotation mark
      '\u2019': '\'', // Right single quotation mark
      '\u201A': '\'', // Single low-9 quotation mark
      '\u201B': '\'', // Single high-reversed-9 quotation mark
      '\u201C': '"', // Left double quotation mark
      '\u201D': '"', // Right double quotation mark
      '\u201E': '"', // Double low-9 quotation mark
      '\u201F': '"', // Double high-reversed-9 quotation mark
      '\u00BC': '1/4', // Vulgar fraction one quarter
      '\u00BD': '1/2', // Vulgar fraction one half
      '\u00BE': '3/4' // Vulgar fraction three quarters
    };
    this.findBar = options.findBar || null;

    // Compile the regular expression for text normalization once
    var replace = Object.keys(this.charactersToNormalize).join('');
    this.normalizationRegex = new RegExp('[' + replace + ']', 'g');

    var events = [
      'find',
      'findagain',
      'findhighlightallchange',
      'findcasesensitivitychange'
    ];

    this.firstPagePromise = new Promise(function (resolve) {
      this.resolveFirstPage = resolve;
    }.bind(this));
    this.handleEvent = this.handleEvent.bind(this);

    for (var i = 0, len = events.length; i < len; i++) {
      window.addEventListener(events[i], this.handleEvent);
    }
  }

  PDFFindController.prototype = {
    setFindBar: function PDFFindController_setFindBar(findBar) {
      this.findBar = findBar;
    },

    reset: function PDFFindController_reset() {
      this.startedTextExtraction = false;
      this.extractTextPromises = [];
      this.active = false;
    },

    normalize: function PDFFindController_normalize(text) {
      var self = this;
      return text.replace(this.normalizationRegex, function (ch) {
        return self.charactersToNormalize[ch];
      });
    },

    calcFindMatch: function PDFFindController_calcFindMatch(pageIndex) {
      var pageContent = this.normalize(this.pageContents[pageIndex]);
      var query = this.normalize(this.state.query);
      var caseSensitive = this.state.caseSensitive;
      var queryLen = query.length;

      if (queryLen === 0) {
        return; // Do nothing: the matches should be wiped out already.
      }

      if (!caseSensitive) {
        pageContent = pageContent.toLowerCase();
        query = query.toLowerCase();
      }

      var matches = [];
      var matchIdx = -queryLen;
      while (true) {
        matchIdx = pageContent.indexOf(query, matchIdx + queryLen);
        if (matchIdx === -1) {
          break;
        }
        matches.push(matchIdx);
      }
      this.pageMatches[pageIndex] = matches;
      this.updatePage(pageIndex);
      if (this.resumePageIdx === pageIndex) {
        this.resumePageIdx = null;
        this.nextPageMatch();
      }
    },

    extractText: function PDFFindController_extractText() {
      if (this.startedTextExtraction) {
        return;
      }
      this.startedTextExtraction = true;

      this.pageContents = [];
      var extractTextPromisesResolves = [];
      var numPages = this.pdfViewer.pagesCount;
      for (var i = 0; i < numPages; i++) {
        this.extractTextPromises.push(new Promise(function (resolve) {
          extractTextPromisesResolves.push(resolve);
        }));
      }

      var self = this;
      function extractPageText(pageIndex) {
        self.pdfViewer.getPageTextContent(pageIndex).then(
          function textContentResolved(textContent) {
            var textItems = textContent.items;
            var str = [];

            for (var i = 0, len = textItems.length; i < len; i++) {
              str.push(textItems[i].str);
            }

            // Store the pageContent as a string.
            self.pageContents.push(str.join(''));

            extractTextPromisesResolves[pageIndex](pageIndex);
            if ((pageIndex + 1) < self.pdfViewer.pagesCount) {
              extractPageText(pageIndex + 1);
            }
          }
        );
      }
      extractPageText(0);
    },

    handleEvent: function PDFFindController_handleEvent(e) {
      if (this.state === null || e.type !== 'findagain') {
        this.dirtyMatch = true;
      }
      this.state = e.detail;
      this.updateUIState(FindStates.FIND_PENDING);

      this.firstPagePromise.then(function() {
        this.extractText();

        clearTimeout(this.findTimeout);
        if (e.type === 'find') {
          // Only trigger the find action after 250ms of silence.
          this.findTimeout = setTimeout(this.nextMatch.bind(this), 250);
        } else {
          this.nextMatch();
        }
      }.bind(this));
    },

    updatePage: function PDFFindController_updatePage(index) {
      var page = this.pdfViewer.getPageView(index);

      if (this.selected.pageIdx === index) {
        // If the page is selected, scroll the page into view, which triggers
        // rendering the page, which adds the textLayer. Once the textLayer is
        // build, it will scroll onto the selected match.
        this.pdfViewer.scrollPageIntoView(index + 1);
      }

      if (page.textLayer) {
        page.textLayer.updateMatches();
      }
    },

    nextMatch: function PDFFindController_nextMatch() {
      var previous = this.state.findPrevious;
      var currentPageIndex = this.pdfViewer.currentPageNumber - 1;
      var numPages = this.pdfViewer.pagesCount;

      this.active = true;

      if (this.dirtyMatch) {
        // Need to recalculate the matches, reset everything.
        this.dirtyMatch = false;
        this.selected.pageIdx = this.selected.matchIdx = -1;
        this.offset.pageIdx = currentPageIndex;
        this.offset.matchIdx = null;
        this.hadMatch = false;
        this.resumePageIdx = null;
        this.pageMatches = [];
        var self = this;

        for (var i = 0; i < numPages; i++) {
          // Wipe out any previous highlighted matches.
          this.updatePage(i);

          // As soon as the text is extracted start finding the matches.
          if (!(i in this.pendingFindMatches)) {
            this.pendingFindMatches[i] = true;
            this.extractTextPromises[i].then(function(pageIdx) {
              delete self.pendingFindMatches[pageIdx];
              self.calcFindMatch(pageIdx);
            });
          }
        }
      }

      // If there's no query there's no point in searching.
      if (this.state.query === '') {
        this.updateUIState(FindStates.FIND_FOUND);
        return;
      }

      // If we're waiting on a page, we return since we can't do anything else.
      if (this.resumePageIdx) {
        return;
      }

      var offset = this.offset;
      // Keep track of how many pages we should maximally iterate through.
      this.pagesToSearch = numPages;
      // If there's already a matchIdx that means we are iterating through a
      // page's matches.
      if (offset.matchIdx !== null) {
        var numPageMatches = this.pageMatches[offset.pageIdx].length;
        if ((!previous && offset.matchIdx + 1 < numPageMatches) ||
            (previous && offset.matchIdx > 0)) {
          // The simple case; we just have advance the matchIdx to select
          // the next match on the page.
          this.hadMatch = true;
          offset.matchIdx = (previous ? offset.matchIdx - 1 :
                                        offset.matchIdx + 1);
          this.updateMatch(true);
          return;
        }
        // We went beyond the current page's matches, so we advance to
        // the next page.
        this.advanceOffsetPage(previous);
      }
      // Start searching through the page.
      this.nextPageMatch();
    },

    matchesReady: function PDFFindController_matchesReady(matches) {
      var offset = this.offset;
      var numMatches = matches.length;
      var previous = this.state.findPrevious;

      if (numMatches) {
        // There were matches for the page, so initialize the matchIdx.
        this.hadMatch = true;
        offset.matchIdx = (previous ? numMatches - 1 : 0);
        this.updateMatch(true);
        return true;
      } else {
        // No matches, so attempt to search the next page.
        this.advanceOffsetPage(previous);
        if (offset.wrapped) {
          offset.matchIdx = null;
          if (this.pagesToSearch < 0) {
            // No point in wrapping again, there were no matches.
            this.updateMatch(false);
            // while matches were not found, searching for a page 
            // with matches should nevertheless halt.
            return true;
          }
        }
        // Matches were not found (and searching is not done).
        return false;
      }
    },

    nextPageMatch: function PDFFindController_nextPageMatch() {
      if (this.resumePageIdx !== null) {
        console.error('There can only be one pending page.');
      }
      do {
        var pageIdx = this.offset.pageIdx;
        var matches = this.pageMatches[pageIdx];
        if (!matches) {
          // The matches don't exist yet for processing by "matchesReady",
          // so set a resume point for when they do exist.
          this.resumePageIdx = pageIdx;
          break;
        }
      } while (!this.matchesReady(matches));
    },

    advanceOffsetPage: function PDFFindController_advanceOffsetPage(previous) {
      var offset = this.offset;
      var numPages = this.extractTextPromises.length;
      offset.pageIdx = (previous ? offset.pageIdx - 1 : offset.pageIdx + 1);
      offset.matchIdx = null;

      this.pagesToSearch--;
      
      if (offset.pageIdx >= numPages || offset.pageIdx < 0) {
        offset.pageIdx = (previous ? numPages - 1 : 0);
        offset.wrapped = true;
      }
    },

    updateMatch: function PDFFindController_updateMatch(found) {
      var state = FindStates.FIND_NOTFOUND;
      var wrapped = this.offset.wrapped;
      this.offset.wrapped = false;
    
      if (found) {
        var previousPage = this.selected.pageIdx;
        this.selected.pageIdx = this.offset.pageIdx;
        this.selected.matchIdx = this.offset.matchIdx;
        state = (wrapped ? FindStates.FIND_WRAPPED : FindStates.FIND_FOUND);
        // Update the currently selected page to wipe out any selected matches.
        if (previousPage !== -1 && previousPage !== this.selected.pageIdx) {
          this.updatePage(previousPage);
        }
      }
    
      this.updateUIState(state, this.state.findPrevious);
      if (this.selected.pageIdx !== -1) {
        this.updatePage(this.selected.pageIdx);
      }
    },

    updateUIState: function PDFFindController_updateUIState(state, previous) {
      if (this.integratedFind) {
        FirefoxCom.request('updateFindControlState',
                           { result: state, findPrevious: previous });
        return;
      }
      if (this.findBar === null) {
        throw new Error('PDFFindController is not initialized with a ' +
                        'PDFFindBar instance.');
      }
      this.findBar.updateUIState(state, previous);
    }
  };
  return PDFFindController;
})();



var PDFHistory = {
  initialized: false,
  initialDestination: null,

  /**
   * @param {string} fingerprint
   * @param {IPDFLinkService} linkService
   */
  initialize: function pdfHistoryInitialize(fingerprint, linkService) {
    this.initialized = true;
    this.reInitialized = false;
    this.allowHashChange = true;
    this.historyUnlocked = true;

    this.previousHash = window.location.hash.substring(1);
    this.currentBookmark = '';
    this.currentPage = 0;
    this.updatePreviousBookmark = false;
    this.previousBookmark = '';
    this.previousPage = 0;
    this.nextHashParam = '';

    this.fingerprint = fingerprint;
    this.linkService = linkService;
    this.currentUid = this.uid = 0;
    this.current = {};

    var state = window.history.state;
    if (this._isStateObjectDefined(state)) {
      // This corresponds to navigating back to the document
      // from another page in the browser history.
      if (state.target.dest) {
        this.initialDestination = state.target.dest;
      } else {
        linkService.setHash(state.target.hash);
      }
      this.currentUid = state.uid;
      this.uid = state.uid + 1;
      this.current = state.target;
    } else {
      // This corresponds to the loading of a new document.
      if (state && state.fingerprint &&
          this.fingerprint !== state.fingerprint) {
        // Reinitialize the browsing history when a new document
        // is opened in the web viewer.
        this.reInitialized = true;
      }
      this._pushOrReplaceState({ fingerprint: this.fingerprint }, true);
    }

    var self = this;
    window.addEventListener('popstate', function pdfHistoryPopstate(evt) {
      evt.preventDefault();
      evt.stopPropagation();

      if (!self.historyUnlocked) {
        return;
      }
      if (evt.state) {
        // Move back/forward in the history.
        self._goTo(evt.state);
      } else {
        // Handle the user modifying the hash of a loaded document.
        self.previousHash = window.location.hash.substring(1);

        // If the history is empty when the hash changes,
        // update the previous entry in the browser history.
        if (self.uid === 0) {
          var previousParams = (self.previousHash && self.currentBookmark &&
                                self.previousHash !== self.currentBookmark) ?
            { hash: self.currentBookmark, page: self.currentPage } :
            { page: 1 };
          self.historyUnlocked = false;
          self.allowHashChange = false;
          window.history.back();
          self._pushToHistory(previousParams, false, true);
          window.history.forward();
          self.historyUnlocked = true;
        }
        self._pushToHistory({ hash: self.previousHash }, false, true);
        self._updatePreviousBookmark();
      }
    }, false);

    function pdfHistoryBeforeUnload() {
      var previousParams = self._getPreviousParams(null, true);
      if (previousParams) {
        var replacePrevious = (!self.current.dest &&
                               self.current.hash !== self.previousHash);
        self._pushToHistory(previousParams, false, replacePrevious);
        self._updatePreviousBookmark();
      }
      // Remove the event listener when navigating away from the document,
      // since 'beforeunload' prevents Firefox from caching the document.
      window.removeEventListener('beforeunload', pdfHistoryBeforeUnload, false);
    }
    window.addEventListener('beforeunload', pdfHistoryBeforeUnload, false);

    window.addEventListener('pageshow', function pdfHistoryPageShow(evt) {
      // If the entire viewer (including the PDF file) is cached in the browser,
      // we need to reattach the 'beforeunload' event listener since
      // the 'DOMContentLoaded' event is not fired on 'pageshow'.
      window.addEventListener('beforeunload', pdfHistoryBeforeUnload, false);
    }, false);
  },

  _isStateObjectDefined: function pdfHistory_isStateObjectDefined(state) {
    return (state && state.uid >= 0 &&
            state.fingerprint && this.fingerprint === state.fingerprint &&
            state.target && state.target.hash) ? true : false;
  },

  _pushOrReplaceState: function pdfHistory_pushOrReplaceState(stateObj,
                                                              replace) {
    if (replace) {
      window.history.replaceState(stateObj, '', document.URL);
    } else {
      window.history.pushState(stateObj, '', document.URL);
    }
  },

  get isHashChangeUnlocked() {
    if (!this.initialized) {
      return true;
    }
    // If the current hash changes when moving back/forward in the history,
    // this will trigger a 'popstate' event *as well* as a 'hashchange' event.
    // Since the hash generally won't correspond to the exact the position
    // stored in the history's state object, triggering the 'hashchange' event
    // can thus corrupt the browser history.
    //
    // When the hash changes during a 'popstate' event, we *only* prevent the
    // first 'hashchange' event and immediately reset allowHashChange.
    // If it is not reset, the user would not be able to change the hash.

    var temp = this.allowHashChange;
    this.allowHashChange = true;
    return temp;
  },

  _updatePreviousBookmark: function pdfHistory_updatePreviousBookmark() {
    if (this.updatePreviousBookmark &&
        this.currentBookmark && this.currentPage) {
      this.previousBookmark = this.currentBookmark;
      this.previousPage = this.currentPage;
      this.updatePreviousBookmark = false;
    }
  },

  updateCurrentBookmark: function pdfHistoryUpdateCurrentBookmark(bookmark,
                                                                  pageNum) {
    if (this.initialized) {
      this.currentBookmark = bookmark.substring(1);
      this.currentPage = pageNum | 0;
      this._updatePreviousBookmark();
    }
  },

  updateNextHashParam: function pdfHistoryUpdateNextHashParam(param) {
    if (this.initialized) {
      this.nextHashParam = param;
    }
  },

  push: function pdfHistoryPush(params, isInitialBookmark) {
    if (!(this.initialized && this.historyUnlocked)) {
      return;
    }
    if (params.dest && !params.hash) {
      params.hash = (this.current.hash && this.current.dest &&
                     this.current.dest === params.dest) ?
        this.current.hash :
        this.linkService.getDestinationHash(params.dest).split('#')[1];
    }
    if (params.page) {
      params.page |= 0;
    }
    if (isInitialBookmark) {
      var target = window.history.state.target;
      if (!target) {
        // Invoked when the user specifies an initial bookmark,
        // thus setting initialBookmark, when the document is loaded.
        this._pushToHistory(params, false);
        this.previousHash = window.location.hash.substring(1);
      }
      this.updatePreviousBookmark = this.nextHashParam ? false : true;
      if (target) {
        // If the current document is reloaded,
        // avoid creating duplicate entries in the history.
        this._updatePreviousBookmark();
      }
      return;
    }
    if (this.nextHashParam) {
      if (this.nextHashParam === params.hash) {
        this.nextHashParam = null;
        this.updatePreviousBookmark = true;
        return;
      } else {
        this.nextHashParam = null;
      }
    }

    if (params.hash) {
      if (this.current.hash) {
        if (this.current.hash !== params.hash) {
          this._pushToHistory(params, true);
        } else {
          if (!this.current.page && params.page) {
            this._pushToHistory(params, false, true);
          }
          this.updatePreviousBookmark = true;
        }
      } else {
        this._pushToHistory(params, true);
      }
    } else if (this.current.page && params.page &&
               this.current.page !== params.page) {
      this._pushToHistory(params, true);
    }
  },

  _getPreviousParams: function pdfHistory_getPreviousParams(onlyCheckPage,
                                                            beforeUnload) {
    if (!(this.currentBookmark && this.currentPage)) {
      return null;
    } else if (this.updatePreviousBookmark) {
      this.updatePreviousBookmark = false;
    }
    if (this.uid > 0 && !(this.previousBookmark && this.previousPage)) {
      // Prevent the history from getting stuck in the current state,
      // effectively preventing the user from going back/forward in the history.
      //
      // This happens if the current position in the document didn't change when
      // the history was previously updated. The reasons for this are either:
      // 1. The current zoom value is such that the document does not need to,
      //    or cannot, be scrolled to display the destination.
      // 2. The previous destination is broken, and doesn't actally point to a
      //    position within the document.
      //    (This is either due to a bad PDF generator, or the user making a
      //     mistake when entering a destination in the hash parameters.)
      return null;
    }
    if ((!this.current.dest && !onlyCheckPage) || beforeUnload) {
      if (this.previousBookmark === this.currentBookmark) {
        return null;
      }
    } else if (this.current.page || onlyCheckPage) {
      if (this.previousPage === this.currentPage) {
        return null;
      }
    } else {
      return null;
    }
    var params = { hash: this.currentBookmark, page: this.currentPage };
    if (PresentationMode.active) {
      params.hash = null;
    }
    return params;
  },

  _stateObj: function pdfHistory_stateObj(params) {
    return { fingerprint: this.fingerprint, uid: this.uid, target: params };
  },

  _pushToHistory: function pdfHistory_pushToHistory(params,
                                                    addPrevious, overwrite) {
    if (!this.initialized) {
      return;
    }
    if (!params.hash && params.page) {
      params.hash = ('page=' + params.page);
    }
    if (addPrevious && !overwrite) {
      var previousParams = this._getPreviousParams();
      if (previousParams) {
        var replacePrevious = (!this.current.dest &&
                               this.current.hash !== this.previousHash);
        this._pushToHistory(previousParams, false, replacePrevious);
      }
    }
    this._pushOrReplaceState(this._stateObj(params),
                             (overwrite || this.uid === 0));
    this.currentUid = this.uid++;
    this.current = params;
    this.updatePreviousBookmark = true;
  },

  _goTo: function pdfHistory_goTo(state) {
    if (!(this.initialized && this.historyUnlocked &&
          this._isStateObjectDefined(state))) {
      return;
    }
    if (!this.reInitialized && state.uid < this.currentUid) {
      var previousParams = this._getPreviousParams(true);
      if (previousParams) {
        this._pushToHistory(this.current, false);
        this._pushToHistory(previousParams, false);
        this.currentUid = state.uid;
        window.history.back();
        return;
      }
    }
    this.historyUnlocked = false;

    if (state.target.dest) {
      this.linkService.navigateTo(state.target.dest);
    } else {
      this.linkService.setHash(state.target.hash);
    }
    this.currentUid = state.uid;
    if (state.uid > this.uid) {
      this.uid = state.uid;
    }
    this.current = state.target;
    this.updatePreviousBookmark = true;

    var currentHash = window.location.hash.substring(1);
    if (this.previousHash !== currentHash) {
      this.allowHashChange = false;
    }
    this.previousHash = currentHash;

    this.historyUnlocked = true;
  },

  back: function pdfHistoryBack() {
    this.go(-1);
  },

  forward: function pdfHistoryForward() {
    this.go(1);
  },

  go: function pdfHistoryGo(direction) {
    if (this.initialized && this.historyUnlocked) {
      var state = window.history.state;
      if (direction === -1 && state && state.uid > 0) {
        window.history.back();
      } else if (direction === 1 && state && state.uid < (this.uid - 1)) {
        window.history.forward();
      }
    }
  }
};


var SecondaryToolbar = {
  opened: false,
  previousContainerHeight: null,
  newContainerHeight: null,

  initialize: function secondaryToolbarInitialize(options) {
    this.toolbar = options.toolbar;
    this.presentationMode = options.presentationMode;
    this.documentProperties = options.documentProperties;
    this.buttonContainer = this.toolbar.firstElementChild;

    // Define the toolbar buttons.
    this.toggleButton = options.toggleButton;
    this.presentationModeButton = options.presentationModeButton;
    this.openFile = options.openFile;
    this.print = options.print;
    this.download = options.download;
    this.viewBookmark = options.viewBookmark;
    this.firstPage = options.firstPage;
    this.lastPage = options.lastPage;
    this.pageRotateCw = options.pageRotateCw;
    this.pageRotateCcw = options.pageRotateCcw;
    this.documentPropertiesButton = options.documentPropertiesButton;

    // Attach the event listeners.
    var elements = [
      // Button to toggle the visibility of the secondary toolbar:
      { element: this.toggleButton, handler: this.toggle },
      // All items within the secondary toolbar
      // (except for toggleHandTool, hand_tool.js is responsible for it):
      { element: this.presentationModeButton,
        handler: this.presentationModeClick },
      { element: this.openFile, handler: this.openFileClick },
      { element: this.print, handler: this.printClick },
      { element: this.download, handler: this.downloadClick },
      { element: this.viewBookmark, handler: this.viewBookmarkClick },
      { element: this.firstPage, handler: this.firstPageClick },
      { element: this.lastPage, handler: this.lastPageClick },
      { element: this.pageRotateCw, handler: this.pageRotateCwClick },
      { element: this.pageRotateCcw, handler: this.pageRotateCcwClick },
      { element: this.documentPropertiesButton,
        handler: this.documentPropertiesClick }
    ];

    for (var item in elements) {
      var element = elements[item].element;
      if (element) {
        element.addEventListener('click', elements[item].handler.bind(this));
      }
    }
  },

  // Event handling functions.
  presentationModeClick: function secondaryToolbarPresentationModeClick(evt) {
    this.presentationMode.request();
    this.close();
  },

  openFileClick: function secondaryToolbarOpenFileClick(evt) {
    document.getElementById('fileInput').click();
    this.close();
  },

  printClick: function secondaryToolbarPrintClick(evt) {
    window.print();
    this.close();
  },

  downloadClick: function secondaryToolbarDownloadClick(evt) {
    PDFViewerApplication.download();
    this.close();
  },

  viewBookmarkClick: function secondaryToolbarViewBookmarkClick(evt) {
    this.close();
  },

  firstPageClick: function secondaryToolbarFirstPageClick(evt) {
    PDFViewerApplication.page = 1;
    this.close();
  },

  lastPageClick: function secondaryToolbarLastPageClick(evt) {
    if (PDFViewerApplication.pdfDocument) {
      PDFViewerApplication.page = PDFViewerApplication.pagesCount;
    }
    this.close();
  },

  pageRotateCwClick: function secondaryToolbarPageRotateCwClick(evt) {
    PDFViewerApplication.rotatePages(90);
  },

  pageRotateCcwClick: function secondaryToolbarPageRotateCcwClick(evt) {
    PDFViewerApplication.rotatePages(-90);
  },

  documentPropertiesClick: function secondaryToolbarDocumentPropsClick(evt) {
    this.documentProperties.open();
    this.close();
  },

  // Misc. functions for interacting with the toolbar.
  setMaxHeight: function secondaryToolbarSetMaxHeight(container) {
    if (!container || !this.buttonContainer) {
      return;
    }
    this.newContainerHeight = container.clientHeight;
    if (this.previousContainerHeight === this.newContainerHeight) {
      return;
    }
    this.buttonContainer.setAttribute('style',
      'max-height: ' + (this.newContainerHeight - SCROLLBAR_PADDING) + 'px;');
    this.previousContainerHeight = this.newContainerHeight;
  },

  open: function secondaryToolbarOpen() {
    if (this.opened) {
      return;
    }
    this.opened = true;
    this.toggleButton.classList.add('toggled');
    this.toolbar.classList.remove('hidden');
  },

  close: function secondaryToolbarClose(target) {
    if (!this.opened) {
      return;
    } else if (target && !this.toolbar.contains(target)) {
      return;
    }
    this.opened = false;
    this.toolbar.classList.add('hidden');
    this.toggleButton.classList.remove('toggled');
  },

  toggle: function secondaryToolbarToggle() {
    if (this.opened) {
      this.close();
    } else {
      this.open();
    }
  }
};


var DELAY_BEFORE_HIDING_CONTROLS = 3000; // in ms
var SELECTOR = 'presentationControls';
var DELAY_BEFORE_RESETTING_SWITCH_IN_PROGRESS = 1000; // in ms

var PresentationMode = {
  active: false,
  args: null,
  contextMenuOpen: false,
  prevCoords: { x: null, y: null },

  initialize: function presentationModeInitialize(options) {
    this.container = options.container;
    this.secondaryToolbar = options.secondaryToolbar;

    this.viewer = this.container.firstElementChild;

    this.firstPage = options.firstPage;
    this.lastPage = options.lastPage;
    this.pageRotateCw = options.pageRotateCw;
    this.pageRotateCcw = options.pageRotateCcw;

    this.firstPage.addEventListener('click', function() {
      this.contextMenuOpen = false;
      this.secondaryToolbar.firstPageClick();
    }.bind(this));
    this.lastPage.addEventListener('click', function() {
      this.contextMenuOpen = false;
      this.secondaryToolbar.lastPageClick();
    }.bind(this));

    this.pageRotateCw.addEventListener('click', function() {
      this.contextMenuOpen = false;
      this.secondaryToolbar.pageRotateCwClick();
    }.bind(this));
    this.pageRotateCcw.addEventListener('click', function() {
      this.contextMenuOpen = false;
      this.secondaryToolbar.pageRotateCcwClick();
    }.bind(this));
  },

  get isFullscreen() {
    return (document.fullscreenElement ||
            document.mozFullScreen ||
            document.webkitIsFullScreen ||
            document.msFullscreenElement);
  },

  /**
   * Initialize a timeout that is used to specify switchInProgress when the
   * browser transitions to fullscreen mode. Since resize events are triggered
   * multiple times during the switch to fullscreen mode, this is necessary in
   * order to prevent the page from being scrolled partially, or completely,
   * out of view when Presentation Mode is enabled.
   * Note: This is only an issue at certain zoom levels, e.g. 'page-width'.
   */
  _setSwitchInProgress: function presentationMode_setSwitchInProgress() {
    if (this.switchInProgress) {
      clearTimeout(this.switchInProgress);
    }
    this.switchInProgress = setTimeout(function switchInProgressTimeout() {
      delete this.switchInProgress;
      this._notifyStateChange();
    }.bind(this), DELAY_BEFORE_RESETTING_SWITCH_IN_PROGRESS);
  },

  _resetSwitchInProgress: function presentationMode_resetSwitchInProgress() {
    if (this.switchInProgress) {
      clearTimeout(this.switchInProgress);
      delete this.switchInProgress;
    }
  },

  request: function presentationModeRequest() {
    if (!PDFViewerApplication.supportsFullscreen || this.isFullscreen ||
        !this.viewer.hasChildNodes()) {
      return false;
    }
    this._setSwitchInProgress();
    this._notifyStateChange();

    if (this.container.requestFullscreen) {
      this.container.requestFullscreen();
    } else if (this.container.mozRequestFullScreen) {
      this.container.mozRequestFullScreen();
    } else if (this.container.webkitRequestFullScreen) {
      this.container.webkitRequestFullScreen(Element.ALLOW_KEYBOARD_INPUT);
    } else if (this.container.msRequestFullscreen) {
      this.container.msRequestFullscreen();
    } else {
      return false;
    }

    this.args = {
      page: PDFViewerApplication.page,
      previousScale: PDFViewerApplication.currentScaleValue
    };

    return true;
  },

  _notifyStateChange: function presentationModeNotifyStateChange() {
    var event = document.createEvent('CustomEvent');
    event.initCustomEvent('presentationmodechanged', true, true, {
      active: PresentationMode.active,
      switchInProgress: !!PresentationMode.switchInProgress
    });
    window.dispatchEvent(event);
  },

  enter: function presentationModeEnter() {
    this.active = true;
    this._resetSwitchInProgress();
    this._notifyStateChange();

    // Ensure that the correct page is scrolled into view when entering
    // Presentation Mode, by waiting until fullscreen mode in enabled.
    // Note: This is only necessary in non-Mozilla browsers.
    setTimeout(function enterPresentationModeTimeout() {
      PDFViewerApplication.page = this.args.page;
      PDFViewerApplication.setScale('page-fit', true);
    }.bind(this), 0);

    window.addEventListener('mousemove', this.mouseMove, false);
    window.addEventListener('mousedown', this.mouseDown, false);
    window.addEventListener('contextmenu', this.contextMenu, false);

    this.showControls();
    HandTool.enterPresentationMode();
    this.contextMenuOpen = false;
    this.container.setAttribute('contextmenu', 'viewerContextMenu');

    // Text selection is disabled in Presentation Mode, thus it's not possible
    // for the user to deselect text that is selected (e.g. with "Select all")
    // when entering Presentation Mode, hence we remove any active selection.
    window.getSelection().removeAllRanges();
  },

  exit: function presentationModeExit() {
    var page = PDFViewerApplication.page;

    // Ensure that the correct page is scrolled into view when exiting
    // Presentation Mode, by waiting until fullscreen mode is disabled.
    // Note: This is only necessary in non-Mozilla browsers.
    setTimeout(function exitPresentationModeTimeout() {
      this.active = false;
      this._notifyStateChange();

      PDFViewerApplication.setScale(this.args.previousScale, true);
      PDFViewerApplication.page = page;
      this.args = null;
    }.bind(this), 0);

    window.removeEventListener('mousemove', this.mouseMove, false);
    window.removeEventListener('mousedown', this.mouseDown, false);
    window.removeEventListener('contextmenu', this.contextMenu, false);

    this.hideControls();
    PDFViewerApplication.clearMouseScrollState();
    HandTool.exitPresentationMode();
    this.container.removeAttribute('contextmenu');
    this.contextMenuOpen = false;

    // Ensure that the thumbnail of the current page is visible
    // when exiting presentation mode.
    scrollIntoView(document.getElementById('thumbnailContainer' + page));
  },

  showControls: function presentationModeShowControls() {
    if (this.controlsTimeout) {
      clearTimeout(this.controlsTimeout);
    } else {
      this.container.classList.add(SELECTOR);
    }
    this.controlsTimeout = setTimeout(function hideControlsTimeout() {
      this.container.classList.remove(SELECTOR);
      delete this.controlsTimeout;
    }.bind(this), DELAY_BEFORE_HIDING_CONTROLS);
  },

  hideControls: function presentationModeHideControls() {
    if (!this.controlsTimeout) {
      return;
    }
    this.container.classList.remove(SELECTOR);
    clearTimeout(this.controlsTimeout);
    delete this.controlsTimeout;
  },

  mouseMove: function presentationModeMouseMove(evt) {
    // Workaround for a bug in WebKit browsers that causes the 'mousemove' event
    // to be fired when the cursor is changed. For details, see:
    // http://code.google.com/p/chromium/issues/detail?id=103041.

    var currCoords = { x: evt.clientX, y: evt.clientY };
    var prevCoords = PresentationMode.prevCoords;
    PresentationMode.prevCoords = currCoords;

    if (currCoords.x === prevCoords.x && currCoords.y === prevCoords.y) {
      return;
    }
    PresentationMode.showControls();
  },

  mouseDown: function presentationModeMouseDown(evt) {
    var self = PresentationMode;
    if (self.contextMenuOpen) {
      self.contextMenuOpen = false;
      evt.preventDefault();
      return;
    }

    if (evt.button === 0) {
      // Enable clicking of links in presentation mode. Please note:
      // Only links pointing to destinations in the current PDF document work.
      var isInternalLink = (evt.target.href &&
                            evt.target.classList.contains('internalLink'));
      if (!isInternalLink) {
        // Unless an internal link was clicked, advance one page.
        evt.preventDefault();
        PDFViewerApplication.page += (evt.shiftKey ? -1 : 1);
      }
    }
  },

  contextMenu: function presentationModeContextMenu(evt) {
    PresentationMode.contextMenuOpen = true;
  }
};

(function presentationModeClosure() {
  function presentationModeChange(e) {
    if (PresentationMode.isFullscreen) {
      PresentationMode.enter();
    } else {
      PresentationMode.exit();
    }
  }

  window.addEventListener('fullscreenchange', presentationModeChange, false);
  window.addEventListener('mozfullscreenchange', presentationModeChange, false);
  window.addEventListener('webkitfullscreenchange', presentationModeChange,
                          false);
  window.addEventListener('MSFullscreenChange', presentationModeChange, false);
})();


/* Copyright 2013 Rob Wu <gwnRob@gmail.com>
 * https://github.com/Rob--W/grab-to-pan.js
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

'use strict';

var GrabToPan = (function GrabToPanClosure() {
  /**
   * Construct a GrabToPan instance for a given HTML element.
   * @param options.element {Element}
   * @param options.ignoreTarget {function} optional. See `ignoreTarget(node)`
   * @param options.onActiveChanged {function(boolean)} optional. Called
   *  when grab-to-pan is (de)activated. The first argument is a boolean that
   *  shows whether grab-to-pan is activated.
   */
  function GrabToPan(options) {
    this.element = options.element;
    this.document = options.element.ownerDocument;
    if (typeof options.ignoreTarget === 'function') {
      this.ignoreTarget = options.ignoreTarget;
    }
    this.onActiveChanged = options.onActiveChanged;

    // Bind the contexts to ensure that `this` always points to
    // the GrabToPan instance.
    this.activate = this.activate.bind(this);
    this.deactivate = this.deactivate.bind(this);
    this.toggle = this.toggle.bind(this);
    this._onmousedown = this._onmousedown.bind(this);
    this._onmousemove = this._onmousemove.bind(this);
    this._endPan = this._endPan.bind(this);

    // This overlay will be inserted in the document when the mouse moves during
    // a grab operation, to ensure that the cursor has the desired appearance.
    var overlay = this.overlay = document.createElement('div');
    overlay.className = 'grab-to-pan-grabbing';
  }
  GrabToPan.prototype = {
    /**
     * Class name of element which can be grabbed
     */
    CSS_CLASS_GRAB: 'grab-to-pan-grab',

    /**
     * Bind a mousedown event to the element to enable grab-detection.
     */
    activate: function GrabToPan_activate() {
      if (!this.active) {
        this.active = true;
        this.element.addEventListener('mousedown', this._onmousedown, true);
        this.element.classList.add(this.CSS_CLASS_GRAB);
        if (this.onActiveChanged) {
          this.onActiveChanged(true);
        }
      }
    },

    /**
     * Removes all events. Any pending pan session is immediately stopped.
     */
    deactivate: function GrabToPan_deactivate() {
      if (this.active) {
        this.active = false;
        this.element.removeEventListener('mousedown', this._onmousedown, true);
        this._endPan();
        this.element.classList.remove(this.CSS_CLASS_GRAB);
        if (this.onActiveChanged) {
          this.onActiveChanged(false);
        }
      }
    },

    toggle: function GrabToPan_toggle() {
      if (this.active) {
        this.deactivate();
      } else {
        this.activate();
      }
    },

    /**
     * Whether to not pan if the target element is clicked.
     * Override this method to change the default behaviour.
     *
     * @param node {Element} The target of the event
     * @return {boolean} Whether to not react to the click event.
     */
    ignoreTarget: function GrabToPan_ignoreTarget(node) {
      // Use matchesSelector to check whether the clicked element
      // is (a child of) an input element / link
      return node[matchesSelector](
        'a[href], a[href] *, input, textarea, button, button *, select, option'
      );
    },

    /**
     * @private
     */
    _onmousedown: function GrabToPan__onmousedown(event) {
      if (event.button !== 0 || this.ignoreTarget(event.target)) {
        return;
      }
      if (event.originalTarget) {
        try {
          /* jshint expr:true */
          event.originalTarget.tagName;
        } catch (e) {
          // Mozilla-specific: element is a scrollbar (XUL element)
          return;
        }
      }

      this.scrollLeftStart = this.element.scrollLeft;
      this.scrollTopStart = this.element.scrollTop;
      this.clientXStart = event.clientX;
      this.clientYStart = event.clientY;
      this.document.addEventListener('mousemove', this._onmousemove, true);
      this.document.addEventListener('mouseup', this._endPan, true);
      // When a scroll event occurs before a mousemove, assume that the user
      // dragged a scrollbar (necessary for Opera Presto, Safari and IE)
      // (not needed for Chrome/Firefox)
      this.element.addEventListener('scroll', this._endPan, true);
      event.preventDefault();
      event.stopPropagation();
      this.document.documentElement.classList.add(this.CSS_CLASS_GRABBING);

      var focusedElement = document.activeElement;
      if (focusedElement && !focusedElement.contains(event.target)) {
        focusedElement.blur();
      }
    },

    /**
     * @private
     */
    _onmousemove: function GrabToPan__onmousemove(event) {
      this.element.removeEventListener('scroll', this._endPan, true);
      if (isLeftMouseReleased(event)) {
        this._endPan();
        return;
      }
      var xDiff = event.clientX - this.clientXStart;
      var yDiff = event.clientY - this.clientYStart;
      this.element.scrollTop = this.scrollTopStart - yDiff;
      this.element.scrollLeft = this.scrollLeftStart - xDiff;
      if (!this.overlay.parentNode) {
        document.body.appendChild(this.overlay);
      }
    },

    /**
     * @private
     */
    _endPan: function GrabToPan__endPan() {
      this.element.removeEventListener('scroll', this._endPan, true);
      this.document.removeEventListener('mousemove', this._onmousemove, true);
      this.document.removeEventListener('mouseup', this._endPan, true);
      if (this.overlay.parentNode) {
        this.overlay.parentNode.removeChild(this.overlay);
      }
    }
  };

  // Get the correct (vendor-prefixed) name of the matches method.
  var matchesSelector;
  ['webkitM', 'mozM', 'msM', 'oM', 'm'].some(function(prefix) {
    var name = prefix + 'atches';
    if (name in document.documentElement) {
      matchesSelector = name;
    }
    name += 'Selector';
    if (name in document.documentElement) {
      matchesSelector = name;
    }
    return matchesSelector; // If found, then truthy, and [].some() ends.
  });

  // Browser sniffing because it's impossible to feature-detect
  // whether event.which for onmousemove is reliable
  var isNotIEorIsIE10plus = !document.documentMode || document.documentMode > 9;
  var chrome = window.chrome;
  var isChrome15OrOpera15plus = chrome && (chrome.webstore || chrome.app);
  //                                       ^ Chrome 15+       ^ Opera 15+
  var isSafari6plus = /Apple/.test(navigator.vendor) &&
                      /Version\/([6-9]\d*|[1-5]\d+)/.test(navigator.userAgent);

  /**
   * Whether the left mouse is not pressed.
   * @param event {MouseEvent}
   * @return {boolean} True if the left mouse button is not pressed.
   *                   False if unsure or if the left mouse button is pressed.
   */
  function isLeftMouseReleased(event) {
    if ('buttons' in event && isNotIEorIsIE10plus) {
      // http://www.w3.org/TR/DOM-Level-3-Events/#events-MouseEvent-buttons
      // Firefox 15+
      // Internet Explorer 10+
      return !(event.buttons | 1);
    }
    if (isChrome15OrOpera15plus || isSafari6plus) {
      // Chrome 14+
      // Opera 15+
      // Safari 6.0+
      return event.which === 0;
    }
  }

  return GrabToPan;
})();

var HandTool = {
  initialize: function handToolInitialize(options) {
    var toggleHandTool = options.toggleHandTool;
    this.handTool = new GrabToPan({
      element: options.container,
      onActiveChanged: function(isActive) {
        if (!toggleHandTool) {
          return;
        }
        if (isActive) {
          toggleHandTool.title =
            mozL10n.get('hand_tool_disable.title', null, 'Disable hand tool');
          toggleHandTool.firstElementChild.textContent =
            mozL10n.get('hand_tool_disable_label', null, 'Disable hand tool');
        } else {
          toggleHandTool.title =
            mozL10n.get('hand_tool_enable.title', null, 'Enable hand tool');
          toggleHandTool.firstElementChild.textContent =
            mozL10n.get('hand_tool_enable_label', null, 'Enable hand tool');
        }
      }
    });
    if (toggleHandTool) {
      toggleHandTool.addEventListener('click', this.toggle.bind(this), false);

      window.addEventListener('localized', function (evt) {
        Preferences.get('enableHandToolOnLoad').then(function resolved(value) {
          if (value) {
            this.handTool.activate();
          }
        }.bind(this), function rejected(reason) {});
      }.bind(this));
    }
  },

  toggle: function handToolToggle() {
    this.handTool.toggle();
    SecondaryToolbar.close();
  },

  enterPresentationMode: function handToolEnterPresentationMode() {
    if (this.handTool.active) {
      this.wasActive = true;
      this.handTool.deactivate();
    }
  },

  exitPresentationMode: function handToolExitPresentationMode() {
    if (this.wasActive) {
      this.wasActive = null;
      this.handTool.activate();
    }
  }
};


var OverlayManager = {
  overlays: {},
  active: null,

  /**
   * @param {string} name The name of the overlay that is registered. This must
   *                 be equal to the ID of the overlay's DOM element.
   * @param {function} callerCloseMethod (optional) The method that, if present,
   *                   will call OverlayManager.close from the Object
   *                   registering the overlay. Access to this method is
   *                   necessary in order to run cleanup code when e.g.
   *                   the overlay is force closed. The default is null.
   * @param {boolean} canForceClose (optional) Indicates if opening the overlay
   *                  will close an active overlay. The default is false.
   * @returns {Promise} A promise that is resolved when the overlay has been
   *                    registered.
   */
  register: function overlayManagerRegister(name,
                                            callerCloseMethod, canForceClose) {
    return new Promise(function (resolve) {
      var element, container;
      if (!name || !(element = document.getElementById(name)) ||
          !(container = element.parentNode)) {
        throw new Error('Not enough parameters.');
      } else if (this.overlays[name]) {
        throw new Error('The overlay is already registered.');
      }
      this.overlays[name] = { element: element,
                              container: container,
                              callerCloseMethod: (callerCloseMethod || null),
                              canForceClose: (canForceClose || false) };
      resolve();
    }.bind(this));
  },

  /**
   * @param {string} name The name of the overlay that is unregistered.
   * @returns {Promise} A promise that is resolved when the overlay has been
   *                    unregistered.
   */
  unregister: function overlayManagerUnregister(name) {
    return new Promise(function (resolve) {
      if (!this.overlays[name]) {
        throw new Error('The overlay does not exist.');
      } else if (this.active === name) {
        throw new Error('The overlay cannot be removed while it is active.');
      }
      delete this.overlays[name];

      resolve();
    }.bind(this));
  },

  /**
   * @param {string} name The name of the overlay that should be opened.
   * @returns {Promise} A promise that is resolved when the overlay has been
   *                    opened.
   */
  open: function overlayManagerOpen(name) {
    return new Promise(function (resolve) {
      if (!this.overlays[name]) {
        throw new Error('The overlay does not exist.');
      } else if (this.active) {
        if (this.overlays[name].canForceClose) {
          this._closeThroughCaller();
        } else if (this.active === name) {
          throw new Error('The overlay is already active.');
        } else {
          throw new Error('Another overlay is currently active.');
        }
      }
      this.active = name;
      this.overlays[this.active].element.classList.remove('hidden');
      this.overlays[this.active].container.classList.remove('hidden');

      window.addEventListener('keydown', this._keyDown);
      resolve();
    }.bind(this));
  },

  /**
   * @param {string} name The name of the overlay that should be closed.
   * @returns {Promise} A promise that is resolved when the overlay has been
   *                    closed.
   */
  close: function overlayManagerClose(name) {
    return new Promise(function (resolve) {
      if (!this.overlays[name]) {
        throw new Error('The overlay does not exist.');
      } else if (!this.active) {
        throw new Error('The overlay is currently not active.');
      } else if (this.active !== name) {
        throw new Error('Another overlay is currently active.');
      }
      this.overlays[this.active].container.classList.add('hidden');
      this.overlays[this.active].element.classList.add('hidden');
      this.active = null;

      window.removeEventListener('keydown', this._keyDown);
      resolve();
    }.bind(this));
  },

  /**
   * @private
   */
  _keyDown: function overlayManager_keyDown(evt) {
    var self = OverlayManager;
    if (self.active && evt.keyCode === 27) { // Esc key.
      self._closeThroughCaller();
      evt.preventDefault();
    }
  },

  /**
   * @private
   */
  _closeThroughCaller: function overlayManager_closeThroughCaller() {
    if (this.overlays[this.active].callerCloseMethod) {
      this.overlays[this.active].callerCloseMethod();
    }
    if (this.active) {
      this.close(this.active);
    }
  }
};


var PasswordPrompt = {
  overlayName: null,
  updatePassword: null,
  reason: null,
  passwordField: null,
  passwordText: null,
  passwordSubmit: null,
  passwordCancel: null,

  initialize: function secondaryToolbarInitialize(options) {
    this.overlayName = options.overlayName;
    this.passwordField = options.passwordField;
    this.passwordText = options.passwordText;
    this.passwordSubmit = options.passwordSubmit;
    this.passwordCancel = options.passwordCancel;

    // Attach the event listeners.
    this.passwordSubmit.addEventListener('click',
      this.verifyPassword.bind(this));

    this.passwordCancel.addEventListener('click', this.close.bind(this));

    this.passwordField.addEventListener('keydown', function (e) {
      if (e.keyCode === 13) { // Enter key
        this.verifyPassword();
      }
    }.bind(this));

    OverlayManager.register(this.overlayName, this.close.bind(this), true);
  },

  open: function passwordPromptOpen() {
    OverlayManager.open(this.overlayName).then(function () {
      this.passwordField.focus();

      var promptString = mozL10n.get('password_label', null,
        'Enter the password to open this PDF file.');

      if (this.reason === PDFJS.PasswordResponses.INCORRECT_PASSWORD) {
        promptString = mozL10n.get('password_invalid', null,
          'Invalid password. Please try again.');
      }

      this.passwordText.textContent = promptString;
    }.bind(this));
  },

  close: function passwordPromptClose() {
    OverlayManager.close(this.overlayName).then(function () {
      this.passwordField.value = '';
    }.bind(this));
  },

  verifyPassword: function passwordPromptVerifyPassword() {
    var password = this.passwordField.value;
    if (password && password.length > 0) {
      this.close();
      return this.updatePassword(password);
    }
  }
};


var DocumentProperties = {
  overlayName: null,
  rawFileSize: 0,

  // Document property fields (in the viewer).
  fileNameField: null,
  fileSizeField: null,
  titleField: null,
  authorField: null,
  subjectField: null,
  keywordsField: null,
  creationDateField: null,
  modificationDateField: null,
  creatorField: null,
  producerField: null,
  versionField: null,
  pageCountField: null,
  url: null,
  pdfDocument: null,

  initialize: function documentPropertiesInitialize(options) {
    this.overlayName = options.overlayName;

    // Set the document property fields.
    this.fileNameField = options.fileNameField;
    this.fileSizeField = options.fileSizeField;
    this.titleField = options.titleField;
    this.authorField = options.authorField;
    this.subjectField = options.subjectField;
    this.keywordsField = options.keywordsField;
    this.creationDateField = options.creationDateField;
    this.modificationDateField = options.modificationDateField;
    this.creatorField = options.creatorField;
    this.producerField = options.producerField;
    this.versionField = options.versionField;
    this.pageCountField = options.pageCountField;

    // Bind the event listener for the Close button.
    if (options.closeButton) {
      options.closeButton.addEventListener('click', this.close.bind(this));
    }

    this.dataAvailablePromise = new Promise(function (resolve) {
      this.resolveDataAvailable = resolve;
    }.bind(this));

    OverlayManager.register(this.overlayName, this.close.bind(this));
  },

  getProperties: function documentPropertiesGetProperties() {
    if (!OverlayManager.active) {
      // If the dialog was closed before dataAvailablePromise was resolved,
      // don't bother updating the properties.
      return;
    }
    // Get the file size (if it hasn't already been set).
    this.pdfDocument.getDownloadInfo().then(function(data) {
      if (data.length === this.rawFileSize) {
        return;
      }
      this.setFileSize(data.length);
      this.updateUI(this.fileSizeField, this.parseFileSize());
    }.bind(this));

    // Get the document properties.
    this.pdfDocument.getMetadata().then(function(data) {
      var fields = [
        { field: this.fileNameField,
          content: getPDFFileNameFromURL(this.url) },
        { field: this.fileSizeField, content: this.parseFileSize() },
        { field: this.titleField, content: data.info.Title },
        { field: this.authorField, content: data.info.Author },
        { field: this.subjectField, content: data.info.Subject },
        { field: this.keywordsField, content: data.info.Keywords },
        { field: this.creationDateField,
          content: this.parseDate(data.info.CreationDate) },
        { field: this.modificationDateField,
          content: this.parseDate(data.info.ModDate) },
        { field: this.creatorField, content: data.info.Creator },
        { field: this.producerField, content: data.info.Producer },
        { field: this.versionField, content: data.info.PDFFormatVersion },
        { field: this.pageCountField, content: this.pdfDocument.numPages }
      ];

      // Show the properties in the dialog.
      for (var item in fields) {
        var element = fields[item];
        this.updateUI(element.field, element.content);
      }
    }.bind(this));
  },

  updateUI: function documentPropertiesUpdateUI(field, content) {
    if (field && content !== undefined && content !== '') {
      field.textContent = content;
    }
  },

  setFileSize: function documentPropertiesSetFileSize(fileSize) {
    if (fileSize > 0) {
      this.rawFileSize = fileSize;
    }
  },

  parseFileSize: function documentPropertiesParseFileSize() {
    var fileSize = this.rawFileSize, kb = fileSize / 1024;
    if (!kb) {
      return;
    } else if (kb < 1024) {
      return mozL10n.get('document_properties_kb', {
        size_kb: (+kb.toPrecision(3)).toLocaleString(),
        size_b: fileSize.toLocaleString()
      }, '{{size_kb}} KB ({{size_b}} bytes)');
    } else {
      return mozL10n.get('document_properties_mb', {
        size_mb: (+(kb / 1024).toPrecision(3)).toLocaleString(),
        size_b: fileSize.toLocaleString()
      }, '{{size_mb}} MB ({{size_b}} bytes)');
    }
  },

  open: function documentPropertiesOpen() {
    Promise.all([OverlayManager.open(this.overlayName),
                 this.dataAvailablePromise]).then(function () {
      this.getProperties();
    }.bind(this));
  },

  close: function documentPropertiesClose() {
    OverlayManager.close(this.overlayName);
  },

  parseDate: function documentPropertiesParseDate(inputDate) {
    // This is implemented according to the PDF specification (see
    // http://www.gnupdf.org/Date for an overview), but note that 
    // Adobe Reader doesn't handle changing the date to universal time
    // and doesn't use the user's time zone (they're effectively ignoring
    // the HH' and mm' parts of the date string).
    var dateToParse = inputDate;
    if (dateToParse === undefined) {
      return '';
    }

    // Remove the D: prefix if it is available.
    if (dateToParse.substring(0,2) === 'D:') {
      dateToParse = dateToParse.substring(2);
    }

    // Get all elements from the PDF date string.
    // JavaScript's Date object expects the month to be between
    // 0 and 11 instead of 1 and 12, so we're correcting for this.
    var year = parseInt(dateToParse.substring(0,4), 10);
    var month = parseInt(dateToParse.substring(4,6), 10) - 1;
    var day = parseInt(dateToParse.substring(6,8), 10);
    var hours = parseInt(dateToParse.substring(8,10), 10);
    var minutes = parseInt(dateToParse.substring(10,12), 10);
    var seconds = parseInt(dateToParse.substring(12,14), 10);
    var utRel = dateToParse.substring(14,15);
    var offsetHours = parseInt(dateToParse.substring(15,17), 10);
    var offsetMinutes = parseInt(dateToParse.substring(18,20), 10);

    // As per spec, utRel = 'Z' means equal to universal time.
    // The other cases ('-' and '+') have to be handled here.
    if (utRel === '-') {
      hours += offsetHours;
      minutes += offsetMinutes;
    } else if (utRel === '+') {
      hours -= offsetHours;
      minutes -= offsetMinutes;
    }

    // Return the new date format from the user's locale.
    var date = new Date(Date.UTC(year, month, day, hours, minutes, seconds));
    var dateString = date.toLocaleDateString();
    var timeString = date.toLocaleTimeString();
    return mozL10n.get('document_properties_date_string',
                       {date: dateString, time: timeString},
                       '{{date}}, {{time}}');
  }
};


var PresentationModeState = {
  UNKNOWN: 0,
  NORMAL: 1,
  CHANGING: 2,
  FULLSCREEN: 3,
};

var IGNORE_CURRENT_POSITION_ON_ZOOM = false;


var CLEANUP_TIMEOUT = 30000;

var RenderingStates = {
  INITIAL: 0,
  RUNNING: 1,
  PAUSED: 2,
  FINISHED: 3
};

/**
 * Controls rendering of the views for pages and thumbnails.
 * @class
 */
var PDFRenderingQueue = (function PDFRenderingQueueClosure() {
  /**
   * @constructs
   */
  function PDFRenderingQueue() {
    this.pdfViewer = null;
    this.pdfThumbnailViewer = null;
    this.onIdle = null;

    this.highestPriorityPage = null;
    this.idleTimeout = null;
    this.printing = false;
    this.isThumbnailViewEnabled = false;
  }

  PDFRenderingQueue.prototype = /** @lends PDFRenderingQueue.prototype */ {
    /**
     * @param {PDFViewer} pdfViewer
     */
    setViewer: function PDFRenderingQueue_setViewer(pdfViewer) {
      this.pdfViewer = pdfViewer;
    },

    /**
     * @param {PDFThumbnailViewer} pdfThumbnailViewer
     */
    setThumbnailViewer:
        function PDFRenderingQueue_setThumbnailViewer(pdfThumbnailViewer) {
      this.pdfThumbnailViewer = pdfThumbnailViewer;
    },

    /**
     * @param {IRenderableView} view
     * @returns {boolean}
     */
    isHighestPriority: function PDFRenderingQueue_isHighestPriority(view) {
      return this.highestPriorityPage === view.renderingId;
    },

    renderHighestPriority: function
        PDFRenderingQueue_renderHighestPriority(currentlyVisiblePages) {
      if (this.idleTimeout) {
        clearTimeout(this.idleTimeout);
        this.idleTimeout = null;
      }

      // Pages have a higher priority than thumbnails, so check them first.
      if (this.pdfViewer.forceRendering(currentlyVisiblePages)) {
        return;
      }
      // No pages needed rendering so check thumbnails.
      if (this.pdfThumbnailViewer && this.isThumbnailViewEnabled) {
        if (this.pdfThumbnailViewer.forceRendering()) {
          return;
        }
      }

      if (this.printing) {
        // If printing is currently ongoing do not reschedule cleanup.
        return;
      }

      if (this.onIdle) {
        this.idleTimeout = setTimeout(this.onIdle.bind(this), CLEANUP_TIMEOUT);
      }
    },

    getHighestPriority: function
        PDFRenderingQueue_getHighestPriority(visible, views, scrolledDown) {
      // The state has changed figure out which page has the highest priority to
      // render next (if any).
      // Priority:
      // 1 visible pages
      // 2 if last scrolled down page after the visible pages
      // 2 if last scrolled up page before the visible pages
      var visibleViews = visible.views;

      var numVisible = visibleViews.length;
      if (numVisible === 0) {
        return false;
      }
      for (var i = 0; i < numVisible; ++i) {
        var view = visibleViews[i].view;
        if (!this.isViewFinished(view)) {
          return view;
        }
      }

      // All the visible views have rendered, try to render next/previous pages.
      if (scrolledDown) {
        var nextPageIndex = visible.last.id;
        // ID's start at 1 so no need to add 1.
        if (views[nextPageIndex] &&
            !this.isViewFinished(views[nextPageIndex])) {
          return views[nextPageIndex];
        }
      } else {
        var previousPageIndex = visible.first.id - 2;
        if (views[previousPageIndex] &&
          !this.isViewFinished(views[previousPageIndex])) {
          return views[previousPageIndex];
        }
      }
      // Everything that needs to be rendered has been.
      return null;
    },

    /**
     * @param {IRenderableView} view
     * @returns {boolean}
     */
    isViewFinished: function PDFRenderingQueue_isViewFinished(view) {
      return view.renderingState === RenderingStates.FINISHED;
    },

    /**
     * Render a page or thumbnail view. This calls the appropriate function
     * based on the views state. If the view is already rendered it will return
     * false.
     * @param {IRenderableView} view
     */
    renderView: function PDFRenderingQueue_renderView(view) {
      var state = view.renderingState;
      switch (state) {
        case RenderingStates.FINISHED:
          return false;
        case RenderingStates.PAUSED:
          this.highestPriorityPage = view.renderingId;
          view.resume();
          break;
        case RenderingStates.RUNNING:
          this.highestPriorityPage = view.renderingId;
          break;
        case RenderingStates.INITIAL:
          this.highestPriorityPage = view.renderingId;
          view.draw(this.renderHighestPriority.bind(this));
          break;
      }
      return true;
    },
  };

  return PDFRenderingQueue;
})();


/**
 * @constructor
 * @param {HTMLDivElement} container - The viewer element.
 * @param {number} id - The page unique ID (normally its number).
 * @param {number} scale - The page scale display.
 * @param {PageViewport} defaultViewport - The page viewport.
 * @param {IPDFLinkService} linkService - The navigation/linking service.
 * @param {PDFRenderingQueue} renderingQueue - The rendering queue object.
 * @param {Cache} cache - The page cache.
 * @param {PDFPageSource} pageSource
 * @param {PDFViewer} viewer
 *
 * @implements {IRenderableView}
 */
var PageView = function pageView(container, id, scale, defaultViewport,
                                 linkService, renderingQueue, cache,
                                 pageSource, viewer) {
  this.id = id;
  this.renderingId = 'page' + id;

  this.rotation = 0;
  this.scale = scale || 1.0;
  this.viewport = defaultViewport;
  this.pdfPageRotate = defaultViewport.rotation;
  this.hasRestrictedScaling = false;

  this.linkService = linkService;
  this.renderingQueue = renderingQueue;
  this.cache = cache;
  this.pageSource = pageSource;
  this.viewer = viewer;

  this.renderingState = RenderingStates.INITIAL;
  this.resume = null;

  this.textLayer = null;

  this.zoomLayer = null;

  this.annotationLayer = null;

  var anchor = document.createElement('a');
  anchor.name = '' + this.id;

  var div = this.el = document.createElement('div');
  div.id = 'pageContainer' + this.id;
  div.className = 'page';
  div.style.width = Math.floor(this.viewport.width) + 'px';
  div.style.height = Math.floor(this.viewport.height) + 'px';

  container.appendChild(anchor);
  container.appendChild(div);

  this.setPdfPage = function pageViewSetPdfPage(pdfPage) {
    this.pdfPage = pdfPage;
    this.pdfPageRotate = pdfPage.rotate;
    var totalRotation = (this.rotation + this.pdfPageRotate) % 360;
    this.viewport = pdfPage.getViewport(this.scale * CSS_UNITS, totalRotation);
    this.stats = pdfPage.stats;
    this.reset();
  };

  this.destroy = function pageViewDestroy() {
    this.zoomLayer = null;
    this.reset();
    if (this.pdfPage) {
      this.pdfPage.destroy();
    }
  };

  this.reset = function pageViewReset(keepAnnotations) {
    if (this.renderTask) {
      this.renderTask.cancel();
    }
    this.resume = null;
    this.renderingState = RenderingStates.INITIAL;

    div.style.width = Math.floor(this.viewport.width) + 'px';
    div.style.height = Math.floor(this.viewport.height) + 'px';

    var childNodes = div.childNodes;
    for (var i = div.childNodes.length - 1; i >= 0; i--) {
      var node = childNodes[i];
      if ((this.zoomLayer && this.zoomLayer === node) ||
          (keepAnnotations && this.annotationLayer === node)) {
        continue;
      }
      div.removeChild(node);
    }
    div.removeAttribute('data-loaded');

    if (keepAnnotations) {
      if (this.annotationLayer) {
        // Hide annotationLayer until all elements are resized
        // so they are not displayed on the already-resized page
        this.annotationLayer.setAttribute('hidden', 'true');
      }
    } else {
      this.annotationLayer = null;
    }

    if (this.canvas) {
      // Zeroing the width and height causes Firefox to release graphics
      // resources immediately, which can greatly reduce memory consumption.
      this.canvas.width = 0;
      this.canvas.height = 0;
      delete this.canvas;
    }

    this.loadingIconDiv = document.createElement('div');
    this.loadingIconDiv.className = 'loadingIcon';
    div.appendChild(this.loadingIconDiv);
  };

  this.update = function pageViewUpdate(scale, rotation) {
    this.scale = scale || this.scale;

    if (typeof rotation !== 'undefined') {
      this.rotation = rotation;
    }

    var totalRotation = (this.rotation + this.pdfPageRotate) % 360;
    this.viewport = this.viewport.clone({
      scale: this.scale * CSS_UNITS,
      rotation: totalRotation
    });

    var isScalingRestricted = false;
    if (this.canvas && PDFJS.maxCanvasPixels > 0) {
      var ctx = this.canvas.getContext('2d');
      var outputScale = getOutputScale(ctx);
      var pixelsInViewport = this.viewport.width * this.viewport.height;
      var maxScale = Math.sqrt(PDFJS.maxCanvasPixels / pixelsInViewport);
      if (((Math.floor(this.viewport.width) * outputScale.sx) | 0) *
          ((Math.floor(this.viewport.height) * outputScale.sy) | 0) >
          PDFJS.maxCanvasPixels) {
        isScalingRestricted = true;
      }
    }

    if (this.canvas &&
        (PDFJS.useOnlyCssZoom ||
          (this.hasRestrictedScaling && isScalingRestricted))) {
      this.cssTransform(this.canvas, true);
      return;
    } else if (this.canvas && !this.zoomLayer) {
      this.zoomLayer = this.canvas.parentNode;
      this.zoomLayer.style.position = 'absolute';
    }
    if (this.zoomLayer) {
      this.cssTransform(this.zoomLayer.firstChild);
    }
    this.reset(true);
  };

  this.cssTransform = function pageCssTransform(canvas, redrawAnnotations) {
    // Scale canvas, canvas wrapper, and page container.
    var width = this.viewport.width;
    var height = this.viewport.height;
    canvas.style.width = canvas.parentNode.style.width = div.style.width =
        Math.floor(width) + 'px';
    canvas.style.height = canvas.parentNode.style.height = div.style.height =
        Math.floor(height) + 'px';
    // The canvas may have been originally rotated, so rotate relative to that.
    var relativeRotation = this.viewport.rotation - canvas._viewport.rotation;
    var absRotation = Math.abs(relativeRotation);
    var scaleX = 1, scaleY = 1;
    if (absRotation === 90 || absRotation === 270) {
      // Scale x and y because of the rotation.
      scaleX = height / width;
      scaleY = width / height;
    }
    var cssTransform = 'rotate(' + relativeRotation + 'deg) ' +
                       'scale(' + scaleX + ',' + scaleY + ')';
    CustomStyle.setProp('transform', canvas, cssTransform);

    if (this.textLayer) {
      // Rotating the text layer is more complicated since the divs inside the
      // the text layer are rotated.
      // TODO: This could probably be simplified by drawing the text layer in
      // one orientation then rotating overall.
      var textLayerViewport = this.textLayer.viewport;
      var textRelativeRotation = this.viewport.rotation -
                                 textLayerViewport.rotation;
      var textAbsRotation = Math.abs(textRelativeRotation);
      var scale = width / textLayerViewport.width;
      if (textAbsRotation === 90 || textAbsRotation === 270) {
        scale = width / textLayerViewport.height;
      }
      var textLayerDiv = this.textLayer.textLayerDiv;
      var transX, transY;
      switch (textAbsRotation) {
        case 0:
          transX = transY = 0;
          break;
        case 90:
          transX = 0;
          transY = '-' + textLayerDiv.style.height;
          break;
        case 180:
          transX = '-' + textLayerDiv.style.width;
          transY = '-' + textLayerDiv.style.height;
          break;
        case 270:
          transX = '-' + textLayerDiv.style.width;
          transY = 0;
          break;
        default:
          console.error('Bad rotation value.');
          break;
      }
      CustomStyle.setProp('transform', textLayerDiv,
                          'rotate(' + textAbsRotation + 'deg) ' +
                            'scale(' + scale + ', ' + scale + ') ' +
                            'translate(' + transX + ', ' + transY + ')');
      CustomStyle.setProp('transformOrigin', textLayerDiv, '0% 0%');
    }

    if (redrawAnnotations && this.annotationLayer) {
      setupAnnotations(div, this.pdfPage, this.viewport);
    }
  };

  Object.defineProperty(this, 'width', {
    get: function PageView_getWidth() {
      return this.viewport.width;
    },
    enumerable: true
  });

  Object.defineProperty(this, 'height', {
    get: function PageView_getHeight() {
      return this.viewport.height;
    },
    enumerable: true
  });

  var self = this;

  function setupAnnotations(pageDiv, pdfPage, viewport) {

    function bindLink(link, dest) {
      link.href = linkService.getDestinationHash(dest);
      link.onclick = function pageViewSetupLinksOnclick() {
        if (dest) {
          linkService.navigateTo(dest);
        }
        return false;
      };
      if (dest) {
        link.className = 'internalLink';
      }
    }

    function bindNamedAction(link, action) {
      link.href = linkService.getAnchorUrl('');
      link.onclick = function pageViewSetupNamedActionOnClick() {
        linkService.executeNamedAction(action);
        return false;
      };
      link.className = 'internalLink';
    }

    pdfPage.getAnnotations().then(function(annotationsData) {
      viewport = viewport.clone({ dontFlip: true });
      var transform = viewport.transform;
      var transformStr = 'matrix(' + transform.join(',') + ')';
      var data, element, i, ii;

      if (self.annotationLayer) {
        // If an annotationLayer already exists, refresh its children's
        // transformation matrices
        for (i = 0, ii = annotationsData.length; i < ii; i++) {
          data = annotationsData[i];
          element = self.annotationLayer.querySelector(
            '[data-annotation-id="' + data.id + '"]');
          if (element) {
            CustomStyle.setProp('transform', element, transformStr);
          }
        }
        // See this.reset()
        self.annotationLayer.removeAttribute('hidden');
      } else {
        for (i = 0, ii = annotationsData.length; i < ii; i++) {
          data = annotationsData[i];
          if (!data || !data.hasHtml) {
            continue;
          }

          element = PDFJS.AnnotationUtils.getHtmlElement(data,
                                                         pdfPage.commonObjs);
          element.setAttribute('data-annotation-id', data.id);
          mozL10n.translate(element);

          var rect = data.rect;
          var view = pdfPage.view;
          rect = PDFJS.Util.normalizeRect([
            rect[0],
            view[3] - rect[1] + view[1],
            rect[2],
            view[3] - rect[3] + view[1]
          ]);
          element.style.left = rect[0] + 'px';
          element.style.top = rect[1] + 'px';
          element.style.position = 'absolute';

          CustomStyle.setProp('transform', element, transformStr);
          var transformOriginStr = -rect[0] + 'px ' + -rect[1] + 'px';
          CustomStyle.setProp('transformOrigin', element, transformOriginStr);

          if (data.subtype === 'Link' && !data.url) {
            var link = element.getElementsByTagName('a')[0];
            if (link) {
              if (data.action) {
                bindNamedAction(link, data.action);
              } else {
                bindLink(link, ('dest' in data) ? data.dest : null);
              }
            }
          }

          if (!self.annotationLayer) {
            var annotationLayerDiv = document.createElement('div');
            annotationLayerDiv.className = 'annotationLayer';
            pageDiv.appendChild(annotationLayerDiv);
            self.annotationLayer = annotationLayerDiv;
          }

          self.annotationLayer.appendChild(element);
        }
      }
    });
  }

  this.getPagePoint = function pageViewGetPagePoint(x, y) {
    return this.viewport.convertToPdfPoint(x, y);
  };

  this.draw = function pageviewDraw(callback) {
    var pdfPage = this.pdfPage;

    if (this.pagePdfPromise) {
      return;
    }
    if (!pdfPage) {
      var promise = this.pageSource.getPage();
      promise.then(function(pdfPage) {
        delete this.pagePdfPromise;
        this.setPdfPage(pdfPage);
        this.draw(callback);
      }.bind(this));
      this.pagePdfPromise = promise;
      return;
    }

    if (this.renderingState !== RenderingStates.INITIAL) {
      console.error('Must be in new state before drawing');
    }

    this.renderingState = RenderingStates.RUNNING;

    var viewport = this.viewport;
    // Wrap the canvas so if it has a css transform for highdpi the overflow
    // will be hidden in FF.
    var canvasWrapper = document.createElement('div');
    canvasWrapper.style.width = div.style.width;
    canvasWrapper.style.height = div.style.height;
    canvasWrapper.classList.add('canvasWrapper');

    var canvas = document.createElement('canvas');
    canvas.id = 'page' + this.id;
    canvasWrapper.appendChild(canvas);
    if (this.annotationLayer) {
      // annotationLayer needs to stay on top
      div.insertBefore(canvasWrapper, this.annotationLayer);
    } else {
      div.appendChild(canvasWrapper);
    }
    this.canvas = canvas;

    var ctx = canvas.getContext('2d');
    var outputScale = getOutputScale(ctx);

    if (PDFJS.useOnlyCssZoom) {
      var actualSizeViewport = viewport.clone({ scale: CSS_UNITS });
      // Use a scale that will make the canvas be the original intended size
      // of the page.
      outputScale.sx *= actualSizeViewport.width / viewport.width;
      outputScale.sy *= actualSizeViewport.height / viewport.height;
      outputScale.scaled = true;
    }

    if (PDFJS.maxCanvasPixels > 0) {
      var pixelsInViewport = viewport.width * viewport.height;
      var maxScale = Math.sqrt(PDFJS.maxCanvasPixels / pixelsInViewport);
      if (outputScale.sx > maxScale || outputScale.sy > maxScale) {
        outputScale.sx = maxScale;
        outputScale.sy = maxScale;
        outputScale.scaled = true;
        this.hasRestrictedScaling = true;
      } else {
        this.hasRestrictedScaling = false;
      }
    }

    canvas.width = (Math.floor(viewport.width) * outputScale.sx) | 0;
    canvas.height = (Math.floor(viewport.height) * outputScale.sy) | 0;
    canvas.style.width = Math.floor(viewport.width) + 'px';
    canvas.style.height = Math.floor(viewport.height) + 'px';
    // Add the viewport so it's known what it was originally drawn with.
    canvas._viewport = viewport;

    var textLayerDiv = null;
    var textLayer = null;
    if (!PDFJS.disableTextLayer) {
      textLayerDiv = document.createElement('div');
      textLayerDiv.className = 'textLayer';
      textLayerDiv.style.width = canvas.style.width;
      textLayerDiv.style.height = canvas.style.height;
      if (this.annotationLayer) {
        // annotationLayer needs to stay on top
        div.insertBefore(textLayerDiv, this.annotationLayer);
      } else {
        div.appendChild(textLayerDiv);
      }

      textLayer = this.viewer.createTextLayerBuilder(textLayerDiv, this.id - 1,
                                                     this.viewport);
    }
    this.textLayer = textLayer;

    // TODO(mack): use data attributes to store these
    ctx._scaleX = outputScale.sx;
    ctx._scaleY = outputScale.sy;
    if (outputScale.scaled) {
      ctx.scale(outputScale.sx, outputScale.sy);
    }

    // Rendering area

    var self = this;
    function pageViewDrawCallback(error) {
      // The renderTask may have been replaced by a new one, so only remove the
      // reference to the renderTask if it matches the one that is triggering
      // this callback.
      if (renderTask === self.renderTask) {
        self.renderTask = null;
      }

      if (error === 'cancelled') {
        return;
      }

      self.renderingState = RenderingStates.FINISHED;

      if (self.loadingIconDiv) {
        div.removeChild(self.loadingIconDiv);
        delete self.loadingIconDiv;
      }

      if (self.zoomLayer) {
        div.removeChild(self.zoomLayer);
        self.zoomLayer = null;
      }

      self.error = error;
      self.stats = pdfPage.stats;
      self.updateStats();
      if (self.onAfterDraw) {
        self.onAfterDraw();
      }

      var event = document.createEvent('CustomEvent');
      event.initCustomEvent('pagerender', true, true, {
        pageNumber: pdfPage.pageNumber
      });
      div.dispatchEvent(event);

      callback();
    }

    var renderContext = {
      canvasContext: ctx,
      viewport: this.viewport,
      // intent: 'default', // === 'display'
      continueCallback: function pdfViewcContinueCallback(cont) {
        if (!self.renderingQueue.isHighestPriority(self)) {
          self.renderingState = RenderingStates.PAUSED;
          self.resume = function resumeCallback() {
            self.renderingState = RenderingStates.RUNNING;
            cont();
          };
          return;
        }
        cont();
      }
    };
    var renderTask = this.renderTask = this.pdfPage.render(renderContext);

    this.renderTask.promise.then(
      function pdfPageRenderCallback() {
        pageViewDrawCallback(null);
        if (textLayer) {
          self.pdfPage.getTextContent().then(
            function textContentResolved(textContent) {
              textLayer.setTextContent(textContent);
            }
          );
        }
      },
      function pdfPageRenderError(error) {
        pageViewDrawCallback(error);
      }
    );

    setupAnnotations(div, pdfPage, this.viewport);
    div.setAttribute('data-loaded', true);

    // Add the page to the cache at the start of drawing. That way it can be
    // evicted from the cache and destroyed even if we pause its rendering.
    cache.push(this);
  };

  this.beforePrint = function pageViewBeforePrint() {
    var pdfPage = this.pdfPage;

    var viewport = pdfPage.getViewport(1);
    // Use the same hack we use for high dpi displays for printing to get better
    // output until bug 811002 is fixed in FF.
    var PRINT_OUTPUT_SCALE = 2;
    var canvas = document.createElement('canvas');
    canvas.width = Math.floor(viewport.width) * PRINT_OUTPUT_SCALE;
    canvas.height = Math.floor(viewport.height) * PRINT_OUTPUT_SCALE;
    canvas.style.width = (PRINT_OUTPUT_SCALE * viewport.width) + 'pt';
    canvas.style.height = (PRINT_OUTPUT_SCALE * viewport.height) + 'pt';
    var cssScale = 'scale(' + (1 / PRINT_OUTPUT_SCALE) + ', ' +
                              (1 / PRINT_OUTPUT_SCALE) + ')';
    CustomStyle.setProp('transform' , canvas, cssScale);
    CustomStyle.setProp('transformOrigin' , canvas, '0% 0%');

    var printContainer = document.getElementById('printContainer');
    var canvasWrapper = document.createElement('div');
    canvasWrapper.style.width = viewport.width + 'pt';
    canvasWrapper.style.height = viewport.height + 'pt';
    canvasWrapper.appendChild(canvas);
    printContainer.appendChild(canvasWrapper);

    canvas.mozPrintCallback = function(obj) {
      var ctx = obj.context;

      ctx.save();
      ctx.fillStyle = 'rgb(255, 255, 255)';
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.restore();
      ctx.scale(PRINT_OUTPUT_SCALE, PRINT_OUTPUT_SCALE);

      var renderContext = {
        canvasContext: ctx,
        viewport: viewport,
        intent: 'print'
      };

      pdfPage.render(renderContext).promise.then(function() {
        // Tell the printEngine that rendering this canvas/page has finished.
        obj.done();
      }, function(error) {
        console.error(error);
        // Tell the printEngine that rendering this canvas/page has failed.
        // This will make the print proces stop.
        if ('abort' in obj) {
          obj.abort();
        } else {
          obj.done();
        }
      });
    };
  };

  this.updateStats = function pageViewUpdateStats() {
    if (!this.stats) {
      return;
    }

    if (PDFJS.pdfBug && Stats.enabled) {
      var stats = this.stats;
      Stats.add(this.id, stats);
    }
  };
};


var FIND_SCROLL_OFFSET_TOP = -50;
var FIND_SCROLL_OFFSET_LEFT = -400;
var MAX_TEXT_DIVS_TO_RENDER = 100000;
var RENDER_DELAY = 200; // ms

var NonWhitespaceRegexp = /\S/;

function isAllWhitespace(str) {
  return !NonWhitespaceRegexp.test(str);
}

/**
 * @typedef {Object} TextLayerBuilderOptions
 * @property {HTMLDivElement} textLayerDiv - The text layer container.
 * @property {number} pageIndex - The page index.
 * @property {PageViewport} viewport - The viewport of the text layer.
 * @property {ILastScrollSource} lastScrollSource - The object that records when
 *   last time scroll happened.
 * @property {boolean} isViewerInPresentationMode
 * @property {PDFFindController} findController
 */

/**
 * TextLayerBuilder provides text-selection functionality for the PDF.
 * It does this by creating overlay divs over the PDF text. These divs
 * contain text that matches the PDF text they are overlaying. This object
 * also provides a way to highlight text that is being searched for.
 * @class
 */
var TextLayerBuilder = (function TextLayerBuilderClosure() {
  function TextLayerBuilder(options) {
    this.textLayerDiv = options.textLayerDiv;
    this.layoutDone = false;
    this.divContentDone = false;
    this.pageIdx = options.pageIndex;
    this.matches = [];
    this.lastScrollSource = options.lastScrollSource || null;
    this.viewport = options.viewport;
    this.isViewerInPresentationMode = options.isViewerInPresentationMode;
    this.textDivs = [];
    this.findController = options.findController || null;
  }

  TextLayerBuilder.prototype = {
    renderLayer: function TextLayerBuilder_renderLayer() {
      var textLayerFrag = document.createDocumentFragment();
      var textDivs = this.textDivs;
      var textDivsLength = textDivs.length;
      var canvas = document.createElement('canvas');
      var ctx = canvas.getContext('2d');

      // No point in rendering many divs as it would make the browser
      // unusable even after the divs are rendered.
      if (textDivsLength > MAX_TEXT_DIVS_TO_RENDER) {
        return;
      }

      var lastFontSize;
      var lastFontFamily;
      for (var i = 0; i < textDivsLength; i++) {
        var textDiv = textDivs[i];
        if (textDiv.dataset.isWhitespace !== undefined) {
          continue;
        }

        var fontSize = textDiv.style.fontSize;
        var fontFamily = textDiv.style.fontFamily;

        // Only build font string and set to context if different from last.
        if (fontSize !== lastFontSize || fontFamily !== lastFontFamily) {
          ctx.font = fontSize + ' ' + fontFamily;
          lastFontSize = fontSize;
          lastFontFamily = fontFamily;
        }

        var width = ctx.measureText(textDiv.textContent).width;
        if (width > 0) {
          textLayerFrag.appendChild(textDiv);
          var transform;
          if (textDiv.dataset.canvasWidth !== undefined) {
            // Dataset values come of type string.
            var textScale = textDiv.dataset.canvasWidth / width;
            transform = 'scaleX(' + textScale + ')';
          } else {
            transform = '';
          }
          var rotation = textDiv.dataset.angle;
          if (rotation) {
            transform = 'rotate(' + rotation + 'deg) ' + transform;
          }
          if (transform) {
            CustomStyle.setProp('transform' , textDiv, transform);
          }
        }
      }

      this.textLayerDiv.appendChild(textLayerFrag);
      this.renderingDone = true;
      this.updateMatches();
    },

    setupRenderLayoutTimer:
        function TextLayerBuilder_setupRenderLayoutTimer() {
      // Schedule renderLayout() if the user has been scrolling,
      // otherwise run it right away.
      var self = this;
      var lastScroll = (this.lastScrollSource === null ?
                        0 : this.lastScrollSource.lastScroll);

      if (Date.now() - lastScroll > RENDER_DELAY) { // Render right away
        this.renderLayer();
      } else { // Schedule
        if (this.renderTimer) {
          clearTimeout(this.renderTimer);
        }
        this.renderTimer = setTimeout(function() {
          self.setupRenderLayoutTimer();
        }, RENDER_DELAY);
      }
    },

    appendText: function TextLayerBuilder_appendText(geom, styles) {
      var style = styles[geom.fontName];
      var textDiv = document.createElement('div');
      this.textDivs.push(textDiv);
      if (isAllWhitespace(geom.str)) {
        textDiv.dataset.isWhitespace = true;
        return;
      }
      var tx = PDFJS.Util.transform(this.viewport.transform, geom.transform);
      var angle = Math.atan2(tx[1], tx[0]);
      if (style.vertical) {
        angle += Math.PI / 2;
      }
      var fontHeight = Math.sqrt((tx[2] * tx[2]) + (tx[3] * tx[3]));
      var fontAscent = fontHeight;
      if (style.ascent) {
        fontAscent = style.ascent * fontAscent;
      } else if (style.descent) {
        fontAscent = (1 + style.descent) * fontAscent;
      }

      var left;
      var top;
      if (angle === 0) {
        left = tx[4];
        top = tx[5] - fontAscent;
      } else {
        left = tx[4] + (fontAscent * Math.sin(angle));
        top = tx[5] - (fontAscent * Math.cos(angle));
      }
      textDiv.style.left = left + 'px';
      textDiv.style.top = top + 'px';
      textDiv.style.fontSize = fontHeight + 'px';
      textDiv.style.fontFamily = style.fontFamily;

      textDiv.textContent = geom.str;
      // |fontName| is only used by the Font Inspector. This test will succeed
      // when e.g. the Font Inspector is off but the Stepper is on, but it's
      // not worth the effort to do a more accurate test.
      if (PDFJS.pdfBug) {
        textDiv.dataset.fontName = geom.fontName;
      }
      // Storing into dataset will convert number into string.
      if (angle !== 0) {
        textDiv.dataset.angle = angle * (180 / Math.PI);
      }
      // We don't bother scaling single-char text divs, because it has very
      // little effect on text highlighting. This makes scrolling on docs with
      // lots of such divs a lot faster.
      if (textDiv.textContent.length > 1) {
        if (style.vertical) {
          textDiv.dataset.canvasWidth = geom.height * this.viewport.scale;
        } else {
          textDiv.dataset.canvasWidth = geom.width * this.viewport.scale;
        }
      }
    },

    setTextContent: function TextLayerBuilder_setTextContent(textContent) {
      this.textContent = textContent;

      var textItems = textContent.items;
      for (var i = 0, len = textItems.length; i < len; i++) {
        this.appendText(textItems[i], textContent.styles);
      }
      this.divContentDone = true;
      this.setupRenderLayoutTimer();
    },

    convertMatches: function TextLayerBuilder_convertMatches(matches) {
      var i = 0;
      var iIndex = 0;
      var bidiTexts = this.textContent.items;
      var end = bidiTexts.length - 1;
      var queryLen = (this.findController === null ?
                      0 : this.findController.state.query.length);
      var ret = [];

      for (var m = 0, len = matches.length; m < len; m++) {
        // Calculate the start position.
        var matchIdx = matches[m];

        // Loop over the divIdxs.
        while (i !== end && matchIdx >= (iIndex + bidiTexts[i].str.length)) {
          iIndex += bidiTexts[i].str.length;
          i++;
        }

        if (i === bidiTexts.length) {
          console.error('Could not find a matching mapping');
        }

        var match = {
          begin: {
            divIdx: i,
            offset: matchIdx - iIndex
          }
        };

        // Calculate the end position.
        matchIdx += queryLen;

        // Somewhat the same array as above, but use > instead of >= to get
        // the end position right.
        while (i !== end && matchIdx > (iIndex + bidiTexts[i].str.length)) {
          iIndex += bidiTexts[i].str.length;
          i++;
        }

        match.end = {
          divIdx: i,
          offset: matchIdx - iIndex
        };
        ret.push(match);
      }

      return ret;
    },

    renderMatches: function TextLayerBuilder_renderMatches(matches) {
      // Early exit if there is nothing to render.
      if (matches.length === 0) {
        return;
      }

      var bidiTexts = this.textContent.items;
      var textDivs = this.textDivs;
      var prevEnd = null;
      var isSelectedPage = (this.findController === null ?
        false : (this.pageIdx === this.findController.selected.pageIdx));
      var selectedMatchIdx = (this.findController === null ?
                              -1 : this.findController.selected.matchIdx);
      var highlightAll = (this.findController === null ?
                          false : this.findController.state.highlightAll);
      var infinity = {
        divIdx: -1,
        offset: undefined
      };

      function beginText(begin, className) {
        var divIdx = begin.divIdx;
        textDivs[divIdx].textContent = '';
        appendTextToDiv(divIdx, 0, begin.offset, className);
      }

      function appendTextToDiv(divIdx, fromOffset, toOffset, className) {
        var div = textDivs[divIdx];
        var content = bidiTexts[divIdx].str.substring(fromOffset, toOffset);
        var node = document.createTextNode(content);
        if (className) {
          var span = document.createElement('span');
          span.className = className;
          span.appendChild(node);
          div.appendChild(span);
          return;
        }
        div.appendChild(node);
      }

      var i0 = selectedMatchIdx, i1 = i0 + 1;
      if (highlightAll) {
        i0 = 0;
        i1 = matches.length;
      } else if (!isSelectedPage) {
        // Not highlighting all and this isn't the selected page, so do nothing.
        return;
      }

      for (var i = i0; i < i1; i++) {
        var match = matches[i];
        var begin = match.begin;
        var end = match.end;
        var isSelected = (isSelectedPage && i === selectedMatchIdx);
        var highlightSuffix = (isSelected ? ' selected' : '');

        if (isSelected && !this.isViewerInPresentationMode) {
          scrollIntoView(textDivs[begin.divIdx],
                         { top: FIND_SCROLL_OFFSET_TOP,
                           left: FIND_SCROLL_OFFSET_LEFT });
        }

        // Match inside new div.
        if (!prevEnd || begin.divIdx !== prevEnd.divIdx) {
          // If there was a previous div, then add the text at the end.
          if (prevEnd !== null) {
            appendTextToDiv(prevEnd.divIdx, prevEnd.offset, infinity.offset);
          }
          // Clear the divs and set the content until the starting point.
          beginText(begin);
        } else {
          appendTextToDiv(prevEnd.divIdx, prevEnd.offset, begin.offset);
        }

        if (begin.divIdx === end.divIdx) {
          appendTextToDiv(begin.divIdx, begin.offset, end.offset,
                          'highlight' + highlightSuffix);
        } else {
          appendTextToDiv(begin.divIdx, begin.offset, infinity.offset,
                          'highlight begin' + highlightSuffix);
          for (var n0 = begin.divIdx + 1, n1 = end.divIdx; n0 < n1; n0++) {
            textDivs[n0].className = 'highlight middle' + highlightSuffix;
          }
          beginText(end, 'highlight end' + highlightSuffix);
        }
        prevEnd = end;
      }

      if (prevEnd) {
        appendTextToDiv(prevEnd.divIdx, prevEnd.offset, infinity.offset);
      }
    },

    updateMatches: function TextLayerBuilder_updateMatches() {
      // Only show matches when all rendering is done.
      if (!this.renderingDone) {
        return;
      }

      // Clear all matches.
      var matches = this.matches;
      var textDivs = this.textDivs;
      var bidiTexts = this.textContent.items;
      var clearedUntilDivIdx = -1;

      // Clear all current matches.
      for (var i = 0, len = matches.length; i < len; i++) {
        var match = matches[i];
        var begin = Math.max(clearedUntilDivIdx, match.begin.divIdx);
        for (var n = begin, end = match.end.divIdx; n <= end; n++) {
          var div = textDivs[n];
          div.textContent = bidiTexts[n].str;
          div.className = '';
        }
        clearedUntilDivIdx = match.end.divIdx + 1;
      }

      if (this.findController === null || !this.findController.active) {
        return;
      }

      // Convert the matches on the page controller into the match format
      // used for the textLayer.
      this.matches = this.convertMatches(this.findController === null ?
        [] : (this.findController.pageMatches[this.pageIdx] || []));
      this.renderMatches(this.matches);
    }
  };
  return TextLayerBuilder;
})();


/**
 * @typedef {Object} PDFViewerOptions
 * @property {HTMLDivElement} container - The container for the viewer element.
 * @property {HTMLDivElement} viewer - (optional) The viewer element.
 * @property {IPDFLinkService} linkService - The navigation/linking service.
 * @property {PDFRenderingQueue} renderingQueue - (optional) The rendering
 *   queue object.
 */

/**
 * Simple viewer control to display PDF content/pages.
 * @class
 * @implements {ILastScrollSource}
 * @implements {IRenderableView}
 */
var PDFViewer = (function pdfViewer() {
  /**
   * @constructs PDFViewer
   * @param {PDFViewerOptions} options
   */
  function PDFViewer(options) {
    this.container = options.container;
    this.viewer = options.viewer || options.container.firstElementChild;
    this.linkService = options.linkService || new SimpleLinkService(this);

    this.defaultRenderingQueue = !options.renderingQueue;
    if (this.defaultRenderingQueue) {
      // Custom rendering queue is not specified, using default one
      this.renderingQueue = new PDFRenderingQueue();
      this.renderingQueue.setViewer(this);
    } else {
      this.renderingQueue = options.renderingQueue;
    }

    this.scroll = watchScroll(this.container, this._scrollUpdate.bind(this));
    this.lastScroll = 0;
    this.updateInProgress = false;
    this.presentationModeState = PresentationModeState.UNKNOWN;
    this._resetView();
  }

  PDFViewer.prototype = /** @lends PDFViewer.prototype */{
    get pagesCount() {
      return this.pages.length;
    },

    getPageView: function (index) {
      return this.pages[index];
    },

    get currentPageNumber() {
      return this._currentPageNumber;
    },

    set currentPageNumber(val) {
      if (!this.pdfDocument) {
        this._currentPageNumber = val;
        return;
      }

      var event = document.createEvent('UIEvents');
      event.initUIEvent('pagechange', true, true, window, 0);
      event.updateInProgress = this.updateInProgress;

      if (!(0 < val && val <= this.pagesCount)) {
        event.pageNumber = this._currentPageNumber;
        event.previousPageNumber = val;
        this.container.dispatchEvent(event);
        return;
      }

      this.pages[val - 1].updateStats();
      event.previousPageNumber = this._currentPageNumber;
      this._currentPageNumber = val;
      event.pageNumber = val;
      this.container.dispatchEvent(event);
    },

    /**
     * @returns {number}
     */
    get currentScale() {
      return this._currentScale;
    },

    /**
     * @param {number} val - Scale of the pages in percents.
     */
    set currentScale(val) {
      if (isNaN(val))  {
        throw new Error('Invalid numeric scale');
      }
      if (!this.pdfDocument) {
        this._currentScale = val;
        this._currentScaleValue = val.toString();
        return;
      }
      this._setScale(val, false);
    },

    /**
     * @returns {string}
     */
    get currentScaleValue() {
      return this._currentScaleValue;
    },

    /**
     * @param val - The scale of the pages (in percent or predefined value).
     */
    set currentScaleValue(val) {
      if (!this.pdfDocument) {
        this._currentScale = isNaN(val) ? UNKNOWN_SCALE : val;
        this._currentScaleValue = val;
        return;
      }
      this._setScale(val, false);
    },

    /**
     * @returns {number}
     */
    get pagesRotation() {
      return this._pagesRotation;
    },

    /**
     * @param {number} rotation - The rotation of the pages (0, 90, 180, 270).
     */
    set pagesRotation(rotation) {
      this._pagesRotation = rotation;

      for (var i = 0, l = this.pages.length; i < l; i++) {
        var page = this.pages[i];
        page.update(page.scale, rotation);
      }

      this._setScale(this._currentScaleValue, true);
    },

    /**
     * @param pdfDocument {PDFDocument}
     */
    setDocument: function (pdfDocument) {
      if (this.pdfDocument) {
        this._resetView();
      }

      this.pdfDocument = pdfDocument;
      if (!pdfDocument) {
        return;
      }

      var pagesCount = pdfDocument.numPages;
      var pagesRefMap = this.pagesRefMap = {};
      var self = this;

      var resolvePagesPromise;
      var pagesPromise = new Promise(function (resolve) {
        resolvePagesPromise = resolve;
      });
      this.pagesPromise = pagesPromise;
      pagesPromise.then(function () {
        var event = document.createEvent('CustomEvent');
        event.initCustomEvent('pagesloaded', true, true, {
          pagesCount: pagesCount
        });
        self.container.dispatchEvent(event);
      });

      var isOnePageRenderedResolved = false;
      var resolveOnePageRendered = null;
      var onePageRendered = new Promise(function (resolve) {
        resolveOnePageRendered = resolve;
      });
      this.onePageRendered = onePageRendered;

      var bindOnAfterDraw = function (pageView) {
        // when page is painted, using the image as thumbnail base
        pageView.onAfterDraw = function pdfViewLoadOnAfterDraw() {
          if (!isOnePageRenderedResolved) {
            isOnePageRenderedResolved = true;
            resolveOnePageRendered();
          }
          var event = document.createEvent('CustomEvent');
          event.initCustomEvent('pagerendered', true, true, {
            pageNumber: pageView.id
          });
          self.container.dispatchEvent(event);
        };
      };

      var firstPagePromise = pdfDocument.getPage(1);
      this.firstPagePromise = firstPagePromise;

      // Fetch a single page so we can get a viewport that will be the default
      // viewport for all pages
      return firstPagePromise.then(function(pdfPage) {
        var scale = this._currentScale || 1.0;
        var viewport = pdfPage.getViewport(scale * CSS_UNITS);
        for (var pageNum = 1; pageNum <= pagesCount; ++pageNum) {
          var pageSource = new PDFPageSource(pdfDocument, pageNum);
          var pageView = new PageView(this.viewer, pageNum, scale,
                                      viewport.clone(), this.linkService,
                                      this.renderingQueue, this.cache,
                                      pageSource, this);
          bindOnAfterDraw(pageView);
          this.pages.push(pageView);
        }

        // Fetch all the pages since the viewport is needed before printing
        // starts to create the correct size canvas. Wait until one page is
        // rendered so we don't tie up too many resources early on.
        onePageRendered.then(function () {
          if (!PDFJS.disableAutoFetch) {
            var getPagesLeft = pagesCount;
            for (var pageNum = 1; pageNum <= pagesCount; ++pageNum) {
              pdfDocument.getPage(pageNum).then(function (pageNum, pdfPage) {
                var pageView = self.pages[pageNum - 1];
                if (!pageView.pdfPage) {
                  pageView.setPdfPage(pdfPage);
                }
                var refStr = pdfPage.ref.num + ' ' + pdfPage.ref.gen + ' R';
                pagesRefMap[refStr] = pageNum;
                getPagesLeft--;
                if (!getPagesLeft) {
                  resolvePagesPromise();
                }
              }.bind(null, pageNum));
            }
          } else {
            // XXX: Printing is semi-broken with auto fetch disabled.
            resolvePagesPromise();
          }
        });

        var event = document.createEvent('CustomEvent');
        event.initCustomEvent('pagesinit', true, true, null);
        self.container.dispatchEvent(event);

        if (this.defaultRenderingQueue) {
          this.update();
        }
      }.bind(this));
    },

    _resetView: function () {
      this.cache = new Cache(DEFAULT_CACHE_SIZE);
      this.pages = [];
      this._currentPageNumber = 1;
      this._currentScale = UNKNOWN_SCALE;
      this._currentScaleValue = null;
      this.location = null;
      this._pagesRotation = 0;

      var container = this.viewer;
      while (container.hasChildNodes()) {
        container.removeChild(container.lastChild);
      }
    },

    _scrollUpdate: function () {
      this.lastScroll = Date.now();

      if (this.pagesCount === 0) {
        return;
      }
      this.update();
    },

    _setScaleUpdatePages: function pdfViewer_setScaleUpdatePages(
        newScale, newValue, noScroll, preset) {
      this._currentScaleValue = newValue;
      if (newScale === this._currentScale) {
        return;
      }
      for (var i = 0, ii = this.pages.length; i < ii; i++) {
        this.pages[i].update(newScale);
      }
      this._currentScale = newScale;

      if (!noScroll) {
        var page = this._currentPageNumber, dest;
        var inPresentationMode =
          this.presentationModeState === PresentationModeState.CHANGING ||
          this.presentationModeState === PresentationModeState.FULLSCREEN;
        if (this.location && !inPresentationMode &&
            !IGNORE_CURRENT_POSITION_ON_ZOOM) {
          page = this.location.pageNumber;
          dest = [null, { name: 'XYZ' }, this.location.left,
            this.location.top, null];
        }
        this.scrollPageIntoView(page, dest);
      }

      var event = document.createEvent('UIEvents');
      event.initUIEvent('scalechange', true, true, window, 0);
      event.scale = newScale;
      if (preset) {
        event.presetValue = newValue;
      }
      this.container.dispatchEvent(event);
    },

    _setScale: function pdfViewer_setScale(value, noScroll) {
      if (value === 'custom') {
        return;
      }
      var scale = parseFloat(value);

      if (scale > 0) {
        this._setScaleUpdatePages(scale, value, noScroll, false);
      } else {
        var currentPage = this.pages[this._currentPageNumber - 1];
        if (!currentPage) {
          return;
        }
        var inPresentationMode =
          this.presentationModeState === PresentationModeState.FULLSCREEN;
        var hPadding = inPresentationMode ? 0 : SCROLLBAR_PADDING;
        var vPadding = inPresentationMode ? 0 : VERTICAL_PADDING;
        var pageWidthScale = (this.container.clientWidth - hPadding) /
                             currentPage.width * currentPage.scale;
        var pageHeightScale = (this.container.clientHeight - vPadding) /
                              currentPage.height * currentPage.scale;
        switch (value) {
          case 'page-actual':
            scale = 1;
            break;
          case 'page-width':
            scale = pageWidthScale;
            break;
          case 'page-height':
            scale = pageHeightScale;
            break;
          case 'page-fit':
            scale = Math.min(pageWidthScale, pageHeightScale);
            break;
          case 'auto':
            var isLandscape = (currentPage.width > currentPage.height);
            // For pages in landscape mode, fit the page height to the viewer
            // *unless* the page would thus become too wide to fit horizontally.
            var horizontalScale = isLandscape ?
              Math.min(pageHeightScale, pageWidthScale) : pageWidthScale;
            scale = Math.min(MAX_AUTO_SCALE, horizontalScale);
            break;
          default:
            console.error('pdfViewSetScale: \'' + value +
              '\' is an unknown zoom value.');
            return;
        }
        this._setScaleUpdatePages(scale, value, noScroll, true);
      }
    },

    /**
     * Scrolls page into view.
     * @param {number} pageNumber
     * @param {Array} dest - (optional) original PDF destination array:
     *   <page-ref> </XYZ|FitXXX> <args..>
     */
    scrollPageIntoView: function PDFViewer_scrollPageIntoView(pageNumber,
                                                              dest) {
      var pageView = this.pages[pageNumber - 1];
      var pageViewDiv = pageView.el;

      if (this.presentationModeState ===
        PresentationModeState.FULLSCREEN) {
        if (this.linkService.page !== pageView.id) {
          // Avoid breaking getVisiblePages in presentation mode.
          this.linkService.page = pageView.id;
          return;
        }
        dest = null;
        // Fixes the case when PDF has different page sizes.
        this._setScale(this.currentScaleValue, true);
      }
      if (!dest) {
        scrollIntoView(pageViewDiv);
        return;
      }

      var x = 0, y = 0;
      var width = 0, height = 0, widthScale, heightScale;
      var changeOrientation = (pageView.rotation % 180 === 0 ? false : true);
      var pageWidth = (changeOrientation ? pageView.height : pageView.width) /
        pageView.scale / CSS_UNITS;
      var pageHeight = (changeOrientation ? pageView.width : pageView.height) /
        pageView.scale / CSS_UNITS;
      var scale = 0;
      switch (dest[1].name) {
        case 'XYZ':
          x = dest[2];
          y = dest[3];
          scale = dest[4];
          // If x and/or y coordinates are not supplied, default to
          // _top_ left of the page (not the obvious bottom left,
          // since aligning the bottom of the intended page with the
          // top of the window is rarely helpful).
          x = x !== null ? x : 0;
          y = y !== null ? y : pageHeight;
          break;
        case 'Fit':
        case 'FitB':
          scale = 'page-fit';
          break;
        case 'FitH':
        case 'FitBH':
          y = dest[2];
          scale = 'page-width';
          break;
        case 'FitV':
        case 'FitBV':
          x = dest[2];
          width = pageWidth;
          height = pageHeight;
          scale = 'page-height';
          break;
        case 'FitR':
          x = dest[2];
          y = dest[3];
          width = dest[4] - x;
          height = dest[5] - y;
          var viewerContainer = this.container;
          widthScale = (viewerContainer.clientWidth - SCROLLBAR_PADDING) /
            width / CSS_UNITS;
          heightScale = (viewerContainer.clientHeight - SCROLLBAR_PADDING) /
            height / CSS_UNITS;
          scale = Math.min(Math.abs(widthScale), Math.abs(heightScale));
          break;
        default:
          return;
      }

      if (scale && scale !== this.currentScale) {
        this.currentScaleValue = scale;
      } else if (this.currentScale === UNKNOWN_SCALE) {
        this.currentScaleValue = DEFAULT_SCALE;
      }

      if (scale === 'page-fit' && !dest[4]) {
        scrollIntoView(pageViewDiv);
        return;
      }

      var boundingRect = [
        pageView.viewport.convertToViewportPoint(x, y),
        pageView.viewport.convertToViewportPoint(x + width, y + height)
      ];
      var left = Math.min(boundingRect[0][0], boundingRect[1][0]);
      var top = Math.min(boundingRect[0][1], boundingRect[1][1]);

      scrollIntoView(pageViewDiv, { left: left, top: top });
    },

    _updateLocation: function (firstPage) {
      var currentScale = this._currentScale;
      var currentScaleValue = this._currentScaleValue;
      var normalizedScaleValue =
        parseFloat(currentScaleValue) === currentScale ?
        Math.round(currentScale * 10000) / 100 : currentScaleValue;

      var pageNumber = firstPage.id;
      var pdfOpenParams = '#page=' + pageNumber;
      pdfOpenParams += '&zoom=' + normalizedScaleValue;
      var currentPageView = this.pages[pageNumber - 1];
      var container = this.container;
      var topLeft = currentPageView.getPagePoint(
        (container.scrollLeft - firstPage.x),
        (container.scrollTop - firstPage.y));
      var intLeft = Math.round(topLeft[0]);
      var intTop = Math.round(topLeft[1]);
      pdfOpenParams += ',' + intLeft + ',' + intTop;

      this.location = {
        pageNumber: pageNumber,
        scale: normalizedScaleValue,
        top: intTop,
        left: intLeft,
        pdfOpenParams: pdfOpenParams
      };
    },

    update: function () {
      var visible = this._getVisiblePages();
      var visiblePages = visible.views;
      if (visiblePages.length === 0) {
        return;
      }

      this.updateInProgress = true;

      var suggestedCacheSize = Math.max(DEFAULT_CACHE_SIZE,
          2 * visiblePages.length + 1);
      this.cache.resize(suggestedCacheSize);

      this.renderingQueue.renderHighestPriority(visible);

      var currentId = this.currentPageNumber;
      var firstPage = visible.first;

      for (var i = 0, ii = visiblePages.length, stillFullyVisible = false;
           i < ii; ++i) {
        var page = visiblePages[i];

        if (page.percent < 100) {
          break;
        }
        if (page.id === currentId) {
          stillFullyVisible = true;
          break;
        }
      }

      if (!stillFullyVisible) {
        currentId = visiblePages[0].id;
      }

      if (this.presentationModeState !== PresentationModeState.FULLSCREEN) {
        this.currentPageNumber = currentId;
      }

      this._updateLocation(firstPage);

      this.updateInProgress = false;

      var event = document.createEvent('UIEvents');
      event.initUIEvent('updateviewarea', true, true, window, 0);
      this.container.dispatchEvent(event);
    },

    containsElement: function (element) {
      return this.container.contains(element);
    },

    focus: function () {
      this.container.focus();
    },

    blur: function () {
      this.container.blur();
    },

    get isHorizontalScrollbarEnabled() {
      return (this.presentationModeState === PresentationModeState.FULLSCREEN ?
        false : (this.container.scrollWidth > this.container.clientWidth));
    },

    _getVisiblePages: function () {
      if (this.presentationModeState !== PresentationModeState.FULLSCREEN) {
        return getVisibleElements(this.container, this.pages, true);
      } else {
        // The algorithm in getVisibleElements doesn't work in all browsers and
        // configurations when presentation mode is active.
        var visible = [];
        var currentPage = this.pages[this._currentPageNumber - 1];
        visible.push({ id: currentPage.id, view: currentPage });
        return { first: currentPage, last: currentPage, views: visible };
      }
    },

    cleanup: function () {
      for (var i = 0, ii = this.pages.length; i < ii; i++) {
        if (this.pages[i] &&
          this.pages[i].renderingState !== RenderingStates.FINISHED) {
          this.pages[i].reset();
        }
      }
    },

    forceRendering: function (currentlyVisiblePages) {
      var visiblePages = currentlyVisiblePages || this._getVisiblePages();
      var pageView = this.renderingQueue.getHighestPriority(visiblePages,
                                                            this.pages,
                                                            this.scroll.down);
      if (pageView) {
        this.renderingQueue.renderView(pageView);
        return true;
      }
      return false;
    },

    getPageTextContent: function (pageIndex) {
      return this.pdfDocument.getPage(pageIndex + 1).then(function (page) {
        return page.getTextContent();
      });
    },

    /**
     * @param textLayerDiv {HTMLDivElement}
     * @param pageIndex {number}
     * @param viewport {PageViewport}
     * @returns {TextLayerBuilder}
     */
    createTextLayerBuilder: function (textLayerDiv, pageIndex, viewport) {
      var isViewerInPresentationMode =
        this.presentationModeState === PresentationModeState.FULLSCREEN;
      return new TextLayerBuilder({
        textLayerDiv: textLayerDiv,
        pageIndex: pageIndex,
        viewport: viewport,
        lastScrollSource: this,
        isViewerInPresentationMode: isViewerInPresentationMode,
        findController: this.findController
      });
    },

    setFindController: function (findController) {
      this.findController = findController;
    },
  };

  return PDFViewer;
})();

var SimpleLinkService = (function SimpleLinkServiceClosure() {
  function SimpleLinkService(pdfViewer) {
    this.pdfViewer = pdfViewer;
  }
  SimpleLinkService.prototype = {
    /**
     * @returns {number}
     */
    get page() {
      return this.pdfViewer.currentPageNumber;
    },
    /**
     * @param {number} value
     */
    set page(value) {
      this.pdfViewer.currentPageNumber = value;
    },
    /**
     * @param dest - The PDF destination object.
     */
    navigateTo: function (dest) {},
    /**
     * @param dest - The PDF destination object.
     * @returns {string} The hyperlink to the PDF object.
     */
    getDestinationHash: function (dest) {
      return '#';
    },
    /**
     * @param hash - The PDF parameters/hash.
     * @returns {string} The hyperlink to the PDF object.
     */
    getAnchorUrl: function (hash) {
      return '#';
    },
    /**
     * @param {string} hash
     */
    setHash: function (hash) {},
    /**
     * @param {string} action
     */
    executeNamedAction: function (action) {},
  };
  return SimpleLinkService;
})();

/**
 * PDFPage object source.
 * @class
 */
var PDFPageSource = (function PDFPageSourceClosure() {
  /**
   * @constructs
   * @param {PDFDocument} pdfDocument
   * @param {number} pageNumber
   * @constructor
   */
  function PDFPageSource(pdfDocument, pageNumber) {
    this.pdfDocument = pdfDocument;
    this.pageNumber = pageNumber;
  }

  PDFPageSource.prototype = /** @lends PDFPageSource.prototype */ {
    /**
     * @returns {Promise<PDFPage>}
     */
    getPage: function () {
      return this.pdfDocument.getPage(this.pageNumber);
    }
  };

  return PDFPageSource;
})();


var PDFViewerApplication = {
  initialBookmark: document.location.hash.substring(1),
  initialized: false,
  fellback: false,
  pdfDocument: null,
  sidebarOpen: false,
  printing: false,
  /** @type {PDFViewer} */
  pdfViewer: null,
  /** @type {PDFThumbnailViewer} */
  pdfThumbnailViewer: null,
  /** @type {PDFRenderingQueue} */
  pdfRenderingQueue: null,
  pageRotation: 0,
  updateScaleControls: true,
  isInitialViewSet: false,
  animationStartedPromise: null,
  mouseScrollTimeStamp: 0,
  mouseScrollDelta: 0,
  preferenceSidebarViewOnLoad: SidebarView.NONE,
  preferencePdfBugEnabled: false,
  isViewerEmbedded: (window.parent !== window),
  url: '',

  // called once when the document is loaded
  initialize: function pdfViewInitialize() {
    var pdfRenderingQueue = new PDFRenderingQueue();
    pdfRenderingQueue.onIdle = this.cleanup.bind(this);
    this.pdfRenderingQueue = pdfRenderingQueue;

    var container = document.getElementById('viewerContainer');
    var viewer = document.getElementById('viewer');
    this.pdfViewer = new PDFViewer({
      container: container,
      viewer: viewer,
      renderingQueue: pdfRenderingQueue,
      linkService: this
    });
    pdfRenderingQueue.setViewer(this.pdfViewer);

    var thumbnailContainer = document.getElementById('thumbnailView');
    this.pdfThumbnailViewer = new PDFThumbnailViewer({
      container: thumbnailContainer,
      renderingQueue: pdfRenderingQueue,
      linkService: this
    });
    pdfRenderingQueue.setThumbnailViewer(this.pdfThumbnailViewer);

    Preferences.initialize();

    this.findController = new PDFFindController({
      pdfViewer: this.pdfViewer,
      integratedFind: this.supportsIntegratedFind
    });
    this.pdfViewer.setFindController(this.findController);

    this.findBar = new PDFFindBar({
      bar: document.getElementById('findbar'),
      toggleButton: document.getElementById('viewFind'),
      findField: document.getElementById('findInput'),
      highlightAllCheckbox: document.getElementById('findHighlightAll'),
      caseSensitiveCheckbox: document.getElementById('findMatchCase'),
      findMsg: document.getElementById('findMsg'),
      findStatusIcon: document.getElementById('findStatusIcon'),
      findPreviousButton: document.getElementById('findPrevious'),
      findNextButton: document.getElementById('findNext'),
      findController: this.findController
    });

    this.findController.setFindBar(this.findBar);

    HandTool.initialize({
      container: container,
      toggleHandTool: document.getElementById('toggleHandTool')
    });

    SecondaryToolbar.initialize({
      toolbar: document.getElementById('secondaryToolbar'),
      presentationMode: PresentationMode,
      toggleButton: document.getElementById('secondaryToolbarToggle'),
      presentationModeButton:
        document.getElementById('secondaryPresentationMode'),
      openFile: document.getElementById('secondaryOpenFile'),
      print: document.getElementById('secondaryPrint'),
      download: document.getElementById('secondaryDownload'),
      viewBookmark: document.getElementById('secondaryViewBookmark'),
      firstPage: document.getElementById('firstPage'),
      lastPage: document.getElementById('lastPage'),
      pageRotateCw: document.getElementById('pageRotateCw'),
      pageRotateCcw: document.getElementById('pageRotateCcw'),
      documentProperties: DocumentProperties,
      documentPropertiesButton: document.getElementById('documentProperties')
    });

    PresentationMode.initialize({
      container: container,
      secondaryToolbar: SecondaryToolbar,
      firstPage: document.getElementById('contextFirstPage'),
      lastPage: document.getElementById('contextLastPage'),
      pageRotateCw: document.getElementById('contextPageRotateCw'),
      pageRotateCcw: document.getElementById('contextPageRotateCcw')
    });

    PasswordPrompt.initialize({
      overlayName: 'passwordOverlay',
      passwordField: document.getElementById('password'),
      passwordText: document.getElementById('passwordText'),
      passwordSubmit: document.getElementById('passwordSubmit'),
      passwordCancel: document.getElementById('passwordCancel')
    });

    DocumentProperties.initialize({
      overlayName: 'documentPropertiesOverlay',
      closeButton: document.getElementById('documentPropertiesClose'),
      fileNameField: document.getElementById('fileNameField'),
      fileSizeField: document.getElementById('fileSizeField'),
      titleField: document.getElementById('titleField'),
      authorField: document.getElementById('authorField'),
      subjectField: document.getElementById('subjectField'),
      keywordsField: document.getElementById('keywordsField'),
      creationDateField: document.getElementById('creationDateField'),
      modificationDateField: document.getElementById('modificationDateField'),
      creatorField: document.getElementById('creatorField'),
      producerField: document.getElementById('producerField'),
      versionField: document.getElementById('versionField'),
      pageCountField: document.getElementById('pageCountField')
    });

    var self = this;
    var initializedPromise = Promise.all([
      Preferences.get('enableWebGL').then(function resolved(value) {
        PDFJS.disableWebGL = !value;
      }),
      Preferences.get('sidebarViewOnLoad').then(function resolved(value) {
        self.preferenceSidebarViewOnLoad = value;
      }),
      Preferences.get('pdfBugEnabled').then(function resolved(value) {
        self.preferencePdfBugEnabled = value;
      }),
      Preferences.get('disableTextLayer').then(function resolved(value) {
        if (PDFJS.disableTextLayer === true) {
          return;
        }
        PDFJS.disableTextLayer = value;
      }),
      Preferences.get('disableRange').then(function resolved(value) {
        if (PDFJS.disableRange === true) {
          return;
        }
        PDFJS.disableRange = value;
      }),
      Preferences.get('disableAutoFetch').then(function resolved(value) {
        PDFJS.disableAutoFetch = value;
      }),
      Preferences.get('disableFontFace').then(function resolved(value) {
        if (PDFJS.disableFontFace === true) {
          return;
        }
        PDFJS.disableFontFace = value;
      }),
      Preferences.get('useOnlyCssZoom').then(function resolved(value) {
        PDFJS.useOnlyCssZoom = value;
      })
      // TODO move more preferences and other async stuff here
    ]).catch(function (reason) { });

    return initializedPromise.then(function () {
      PDFViewerApplication.initialized = true;
    });
  },

  zoomIn: function pdfViewZoomIn(ticks) {
    var newScale = this.pdfViewer.currentScale;
    do {
      newScale = (newScale * DEFAULT_SCALE_DELTA).toFixed(2);
      newScale = Math.ceil(newScale * 10) / 10;
      newScale = Math.min(MAX_SCALE, newScale);
    } while (--ticks && newScale < MAX_SCALE);
    this.setScale(newScale, true);
  },

  zoomOut: function pdfViewZoomOut(ticks) {
    var newScale = this.pdfViewer.currentScale;
    do {
      newScale = (newScale / DEFAULT_SCALE_DELTA).toFixed(2);
      newScale = Math.floor(newScale * 10) / 10;
      newScale = Math.max(MIN_SCALE, newScale);
    } while (--ticks && newScale > MIN_SCALE);
    this.setScale(newScale, true);
  },

  get currentScaleValue() {
    return this.pdfViewer.currentScaleValue;
  },

  get pagesCount() {
    return this.pdfDocument.numPages;
  },

  set page(val) {
    this.pdfViewer.currentPageNumber = val;
  },

  get page() {
    return this.pdfViewer.currentPageNumber;
  },

  get supportsPrinting() {
    var canvas = document.createElement('canvas');
    var value = 'mozPrintCallback' in canvas;
    // shadow
    Object.defineProperty(this, 'supportsPrinting', { value: value,
                                                      enumerable: true,
                                                      configurable: true,
                                                      writable: false });
    return value;
  },

  get supportsFullscreen() {
    var doc = document.documentElement;
    var support = doc.requestFullscreen || doc.mozRequestFullScreen ||
                  doc.webkitRequestFullScreen || doc.msRequestFullscreen;

    if (document.fullscreenEnabled === false ||
        document.mozFullScreenEnabled === false ||
        document.webkitFullscreenEnabled === false ||
        document.msFullscreenEnabled === false) {
      support = false;
    }

    Object.defineProperty(this, 'supportsFullscreen', { value: support,
                                                        enumerable: true,
                                                        configurable: true,
                                                        writable: false });
    return support;
  },

  get supportsIntegratedFind() {
    var support = false;
    Object.defineProperty(this, 'supportsIntegratedFind', { value: support,
                                                            enumerable: true,
                                                            configurable: true,
                                                            writable: false });
    return support;
  },

  get supportsDocumentFonts() {
    var support = true;
    Object.defineProperty(this, 'supportsDocumentFonts', { value: support,
                                                           enumerable: true,
                                                           configurable: true,
                                                           writable: false });
    return support;
  },

  get supportsDocumentColors() {
    var support = true;
    Object.defineProperty(this, 'supportsDocumentColors', { value: support,
                                                            enumerable: true,
                                                            configurable: true,
                                                            writable: false });
    return support;
  },

  get loadingBar() {
    var bar = new ProgressBar('#loadingBar', {});
    Object.defineProperty(this, 'loadingBar', { value: bar,
                                                enumerable: true,
                                                configurable: true,
                                                writable: false });
    return bar;
  },


  setTitleUsingUrl: function pdfViewSetTitleUsingUrl(url) {
    this.url = url;
    try {
      this.setTitle(decodeURIComponent(getFileName(url)) || url);
    } catch (e) {
      // decodeURIComponent may throw URIError,
      // fall back to using the unprocessed url in that case
      this.setTitle(url);
    }
  },

  setTitle: function pdfViewSetTitle(title) {
    document.title = title;
  },

  close: function pdfViewClose() {
    var errorWrapper = document.getElementById('errorWrapper');
    errorWrapper.setAttribute('hidden', 'true');

    if (!this.pdfDocument) {
      return;
    }

    this.pdfDocument.destroy();
    this.pdfDocument = null;

    this.pdfThumbnailViewer.setDocument(null);
    this.pdfViewer.setDocument(null);

    if (typeof PDFBug !== 'undefined') {
      PDFBug.cleanup();
    }
  },

  // TODO(mack): This function signature should really be pdfViewOpen(url, args)
  open: function pdfViewOpen(file, scale, password,
                             pdfDataRangeTransport, args) {
    if (this.pdfDocument) {
      // Reload the preferences if a document was previously opened.
      Preferences.reload();
    }
    this.close();

    var parameters = {password: password};
    if (typeof file === 'string') { // URL
      this.setTitleUsingUrl(file);
      parameters.url = file;
    } else if (file && 'byteLength' in file) { // ArrayBuffer
      parameters.data = file;
    } else if (file.url && file.originalUrl) {
      this.setTitleUsingUrl(file.originalUrl);
      parameters.url = file.url;
    }
    if (args) {
      for (var prop in args) {
        parameters[prop] = args[prop];
      }
    }

    var self = this;
    self.loading = true;
    self.downloadComplete = false;

    var passwordNeeded = function passwordNeeded(updatePassword, reason) {
      PasswordPrompt.updatePassword = updatePassword;
      PasswordPrompt.reason = reason;
      PasswordPrompt.open();
    };

    function getDocumentProgress(progressData) {
      self.progress(progressData.loaded / progressData.total);
    }

    PDFJS.getDocument(parameters, pdfDataRangeTransport, passwordNeeded,
                      getDocumentProgress).then(
      function getDocumentCallback(pdfDocument) {
        self.load(pdfDocument, scale);
        self.loading = false;
      },
      function getDocumentError(exception) {
        var message = exception && exception.message;
        var loadingErrorMessage = mozL10n.get('loading_error', null,
          'An error occurred while loading the PDF.');

        if (exception instanceof PDFJS.InvalidPDFException) {
          // change error message also for other builds
          loadingErrorMessage = mozL10n.get('invalid_file_error', null,
                                            'Invalid or corrupted PDF file.');
        } else if (exception instanceof PDFJS.MissingPDFException) {
          // special message for missing PDF's
          loadingErrorMessage = mozL10n.get('missing_file_error', null,
                                            'Missing PDF file.');
        } else if (exception instanceof PDFJS.UnexpectedResponseException) {
          loadingErrorMessage = mozL10n.get('unexpected_response_error', null,
                                            'Unexpected server response.');
        }

        var moreInfo = {
          message: message
        };
        self.error(loadingErrorMessage, moreInfo);
        self.loading = false;
      }
    );

    if (args && args.length) {
      DocumentProperties.setFileSize(args.length);
    }
  },

  download: function pdfViewDownload() {
    function downloadByUrl() {
      downloadManager.downloadUrl(url, filename);
    }

    var url = this.url.split('#')[0];
    var filename = getPDFFileNameFromURL(url);
    var downloadManager = new DownloadManager();
    downloadManager.onerror = function (err) {
      // This error won't really be helpful because it's likely the
      // fallback won't work either (or is already open).
      PDFViewerApplication.error('PDF failed to download.');
    };

    if (!this.pdfDocument) { // the PDF is not ready yet
      downloadByUrl();
      return;
    }

    if (!this.downloadComplete) { // the PDF is still downloading
      downloadByUrl();
      return;
    }

    this.pdfDocument.getData().then(
      function getDataSuccess(data) {
        var blob = PDFJS.createBlob(data, 'application/pdf');
        downloadManager.download(blob, url, filename);
      },
      downloadByUrl // Error occurred try downloading with just the url.
    ).then(null, downloadByUrl);
  },

  fallback: function pdfViewFallback(featureId) {
    return;
  },

  navigateTo: function pdfViewNavigateTo(dest) {
    var destString = '';
    var self = this;

    var goToDestination = function(destRef) {
      self.pendingRefStr = null;
      // dest array looks like that: <page-ref> </XYZ|FitXXX> <args..>
      var pageNumber = destRef instanceof Object ?
        self.pagesRefMap[destRef.num + ' ' + destRef.gen + ' R'] :
        (destRef + 1);
      if (pageNumber) {
        if (pageNumber > self.pagesCount) {
          pageNumber = self.pagesCount;
        }
        self.pdfViewer.scrollPageIntoView(pageNumber, dest);

        // Update the browsing history.
        PDFHistory.push({ dest: dest, hash: destString, page: pageNumber });
      } else {
        self.pdfDocument.getPageIndex(destRef).then(function (pageIndex) {
          var pageNum = pageIndex + 1;
          self.pagesRefMap[destRef.num + ' ' + destRef.gen + ' R'] = pageNum;
          goToDestination(destRef);
        });
      }
    };

    var destinationPromise;
    if (typeof dest === 'string') {
      destString = dest;
      destinationPromise = this.pdfDocument.getDestination(dest);
    } else {
      destinationPromise = Promise.resolve(dest);
    }
    destinationPromise.then(function(destination) {
      dest = destination;
      if (!(destination instanceof Array)) {
        return; // invalid destination
      }
      goToDestination(destination[0]);
    });
  },

  executeNamedAction: function pdfViewExecuteNamedAction(action) {
    // See PDF reference, table 8.45 - Named action
    switch (action) {
      case 'GoToPage':
        document.getElementById('pageNumber').focus();
        break;

      case 'GoBack':
        PDFHistory.back();
        break;

      case 'GoForward':
        PDFHistory.forward();
        break;

      case 'Find':
        if (!this.supportsIntegratedFind) {
          this.findBar.toggle();
        }
        break;

      case 'NextPage':
        this.page++;
        break;

      case 'PrevPage':
        this.page--;
        break;

      case 'LastPage':
        this.page = this.pagesCount;
        break;

      case 'FirstPage':
        this.page = 1;
        break;

      default:
        break; // No action according to spec
    }
  },

  getDestinationHash: function pdfViewGetDestinationHash(dest) {
    if (typeof dest === 'string') {
      return this.getAnchorUrl('#' + escape(dest));
    }
    if (dest instanceof Array) {
      var destRef = dest[0]; // see navigateTo method for dest format
      var pageNumber = destRef instanceof Object ?
        this.pagesRefMap[destRef.num + ' ' + destRef.gen + ' R'] :
        (destRef + 1);
      if (pageNumber) {
        var pdfOpenParams = this.getAnchorUrl('#page=' + pageNumber);
        var destKind = dest[1];
        if (typeof destKind === 'object' && 'name' in destKind &&
            destKind.name === 'XYZ') {
          var scale = (dest[4] || this.currentScaleValue);
          var scaleNumber = parseFloat(scale);
          if (scaleNumber) {
            scale = scaleNumber * 100;
          }
          pdfOpenParams += '&zoom=' + scale;
          if (dest[2] || dest[3]) {
            pdfOpenParams += ',' + (dest[2] || 0) + ',' + (dest[3] || 0);
          }
        }
        return pdfOpenParams;
      }
    }
    return '';
  },

  /**
   * Prefix the full url on anchor links to make sure that links are resolved
   * relative to the current URL instead of the one defined in <base href>.
   * @param {String} anchor The anchor hash, including the #.
   */
  getAnchorUrl: function getAnchorUrl(anchor) {
    return anchor;
  },

  /**
   * Show the error box.
   * @param {String} message A message that is human readable.
   * @param {Object} moreInfo (optional) Further information about the error
   *                            that is more technical.  Should have a 'message'
   *                            and optionally a 'stack' property.
   */
  error: function pdfViewError(message, moreInfo) {
    var moreInfoText = mozL10n.get('error_version_info',
      {version: PDFJS.version || '?', build: PDFJS.build || '?'},
      'PDF.js v{{version}} (build: {{build}})') + '\n';
    if (moreInfo) {
      moreInfoText +=
        mozL10n.get('error_message', {message: moreInfo.message},
        'Message: {{message}}');
      if (moreInfo.stack) {
        moreInfoText += '\n' +
          mozL10n.get('error_stack', {stack: moreInfo.stack},
          'Stack: {{stack}}');
      } else {
        if (moreInfo.filename) {
          moreInfoText += '\n' +
            mozL10n.get('error_file', {file: moreInfo.filename},
            'File: {{file}}');
        }
        if (moreInfo.lineNumber) {
          moreInfoText += '\n' +
            mozL10n.get('error_line', {line: moreInfo.lineNumber},
            'Line: {{line}}');
        }
      }
    }

    var errorWrapper = document.getElementById('errorWrapper');
    errorWrapper.removeAttribute('hidden');

    var errorMessage = document.getElementById('errorMessage');
    errorMessage.textContent = message;

    var closeButton = document.getElementById('errorClose');
    closeButton.onclick = function() {
      errorWrapper.setAttribute('hidden', 'true');
    };

    var errorMoreInfo = document.getElementById('errorMoreInfo');
    var moreInfoButton = document.getElementById('errorShowMore');
    var lessInfoButton = document.getElementById('errorShowLess');
    moreInfoButton.onclick = function() {
      errorMoreInfo.removeAttribute('hidden');
      moreInfoButton.setAttribute('hidden', 'true');
      lessInfoButton.removeAttribute('hidden');
      errorMoreInfo.style.height = errorMoreInfo.scrollHeight + 'px';
    };
    lessInfoButton.onclick = function() {
      errorMoreInfo.setAttribute('hidden', 'true');
      moreInfoButton.removeAttribute('hidden');
      lessInfoButton.setAttribute('hidden', 'true');
    };
    moreInfoButton.oncontextmenu = noContextMenuHandler;
    lessInfoButton.oncontextmenu = noContextMenuHandler;
    closeButton.oncontextmenu = noContextMenuHandler;
    moreInfoButton.removeAttribute('hidden');
    lessInfoButton.setAttribute('hidden', 'true');
    errorMoreInfo.value = moreInfoText;
  },

  progress: function pdfViewProgress(level) {
    var percent = Math.round(level * 100);
    // When we transition from full request to range requests, it's possible
    // that we discard some of the loaded data. This can cause the loading
    // bar to move backwards. So prevent this by only updating the bar if it
    // increases.
    if (percent > this.loadingBar.percent || isNaN(percent)) {
      this.loadingBar.percent = percent;

      // When disableAutoFetch is enabled, it's not uncommon for the entire file
      // to never be fetched (depends on e.g. the file structure). In this case
      // the loading bar will not be completely filled, nor will it be hidden.
      // To prevent displaying a partially filled loading bar permanently, we
      // hide it when no data has been loaded during a certain amount of time.
      if (PDFJS.disableAutoFetch && percent) {
        if (this.disableAutoFetchLoadingBarTimeout) {
          clearTimeout(this.disableAutoFetchLoadingBarTimeout);
          this.disableAutoFetchLoadingBarTimeout = null;
        }
        this.loadingBar.show();

        this.disableAutoFetchLoadingBarTimeout = setTimeout(function () {
          this.loadingBar.hide();
          this.disableAutoFetchLoadingBarTimeout = null;
        }.bind(this), DISABLE_AUTO_FETCH_LOADING_BAR_TIMEOUT);
      }
    }
  },

  load: function pdfViewLoad(pdfDocument, scale) {
    var self = this;
    scale = scale || UNKNOWN_SCALE;

    this.findController.reset();

    this.pdfDocument = pdfDocument;

    DocumentProperties.url = this.url;
    DocumentProperties.pdfDocument = pdfDocument;
    DocumentProperties.resolveDataAvailable();

    var downloadedPromise = pdfDocument.getDownloadInfo().then(function() {
      self.downloadComplete = true;
      self.loadingBar.hide();
    });

    var pagesCount = pdfDocument.numPages;
    document.getElementById('numPages').textContent =
      mozL10n.get('page_of', {pageCount: pagesCount}, 'of {{pageCount}}');
    document.getElementById('pageNumber').max = pagesCount;

    var id = this.documentFingerprint = pdfDocument.fingerprint;
    var store = this.store = new ViewHistory(id);

    var pdfViewer = this.pdfViewer;
    pdfViewer.currentScale = scale;
    pdfViewer.setDocument(pdfDocument);
    var firstPagePromise = pdfViewer.firstPagePromise;
    var pagesPromise = pdfViewer.pagesPromise;
    var onePageRendered = pdfViewer.onePageRendered;

    this.pageRotation = 0;
    this.isInitialViewSet = false;
    this.pagesRefMap = pdfViewer.pagesRefMap;

    this.pdfThumbnailViewer.setDocument(pdfDocument);

    firstPagePromise.then(function(pdfPage) {
      downloadedPromise.then(function () {
        var event = document.createEvent('CustomEvent');
        event.initCustomEvent('documentload', true, true, {});
        window.dispatchEvent(event);
      });

      self.loadingBar.setWidth(document.getElementById('viewer'));

      self.findController.resolveFirstPage();

      if (!PDFJS.disableHistory && !self.isViewerEmbedded) {
        // The browsing history is only enabled when the viewer is standalone,
        // i.e. not when it is embedded in a web page.
        PDFHistory.initialize(self.documentFingerprint, self);
      }
    });

    // Fetch the necessary preference values.
    var showPreviousViewOnLoad;
    var showPreviousViewOnLoadPromise =
      Preferences.get('showPreviousViewOnLoad').then(function (prefValue) {
        showPreviousViewOnLoad = prefValue;
      });
    var defaultZoomValue;
    var defaultZoomValuePromise =
      Preferences.get('defaultZoomValue').then(function (prefValue) {
        defaultZoomValue = prefValue;
      });

    var storePromise = store.initializedPromise;
    Promise.all([firstPagePromise, storePromise, showPreviousViewOnLoadPromise,
                 defaultZoomValuePromise]).then(function resolved() {
      var storedHash = null;
      if (showPreviousViewOnLoad && store.get('exists', false)) {
        var pageNum = store.get('page', '1');
        var zoom = defaultZoomValue ||
                   store.get('zoom', self.pdfViewer.currentScale);
        var left = store.get('scrollLeft', '0');
        var top = store.get('scrollTop', '0');

        storedHash = 'page=' + pageNum + '&zoom=' + zoom + ',' +
                     left + ',' + top;
      } else if (defaultZoomValue) {
        storedHash = 'page=1&zoom=' + defaultZoomValue;
      }
      self.setInitialView(storedHash, scale);

      // Make all navigation keys work on document load,
      // unless the viewer is embedded in a web page.
      if (!self.isViewerEmbedded) {
        self.pdfViewer.focus();
      }
    }, function rejected(reason) {
      console.error(reason);

      firstPagePromise.then(function () {
        self.setInitialView(null, scale);
      });
    });

    pagesPromise.then(function() {
      if (self.supportsPrinting) {
        pdfDocument.getJavaScript().then(function(javaScript) {
          if (javaScript.length) {
            console.warn('Warning: JavaScript is not supported');
            self.fallback(PDFJS.UNSUPPORTED_FEATURES.javaScript);
          }
          // Hack to support auto printing.
          var regex = /\bprint\s*\(/g;
          for (var i = 0, ii = javaScript.length; i < ii; i++) {
            var js = javaScript[i];
            if (js && regex.test(js)) {
              setTimeout(function() {
                window.print();
              });
              return;
            }
          }
        });
      }
    });

    // outline depends on pagesRefMap
    var promises = [pagesPromise, this.animationStartedPromise];
    Promise.all(promises).then(function() {
      pdfDocument.getOutline().then(function(outline) {
        var outlineView = document.getElementById('outlineView');
        self.outline = new DocumentOutlineView({
          outline: outline,
          outlineView: outlineView,
          linkService: self
        });
        document.getElementById('viewOutline').disabled = !outline;

        if (!outline && !outlineView.classList.contains('hidden')) {
          self.switchSidebarView('thumbs');
        }
        if (outline &&
            self.preferenceSidebarViewOnLoad === SidebarView.OUTLINE) {
          self.switchSidebarView('outline', true);
        }
      });
      pdfDocument.getAttachments().then(function(attachments) {
        var attachmentsView = document.getElementById('attachmentsView');
        self.attachments = new DocumentAttachmentsView({
          attachments: attachments,
          attachmentsView: attachmentsView
        });
        document.getElementById('viewAttachments').disabled = !attachments;

        if (!attachments && !attachmentsView.classList.contains('hidden')) {
          self.switchSidebarView('thumbs');
        }
        if (attachments &&
            self.preferenceSidebarViewOnLoad === SidebarView.ATTACHMENTS) {
          self.switchSidebarView('attachments', true);
        }
      });
    });

    if (self.preferenceSidebarViewOnLoad === SidebarView.THUMBS) {
      Promise.all([firstPagePromise, onePageRendered]).then(function () {
        self.switchSidebarView('thumbs', true);
      });
    }

    pdfDocument.getMetadata().then(function(data) {
      var info = data.info, metadata = data.metadata;
      self.documentInfo = info;
      self.metadata = metadata;

      // Provides some basic debug information
      console.log('PDF ' + pdfDocument.fingerprint + ' [' +
                  info.PDFFormatVersion + ' ' + (info.Producer || '-').trim() +
                  ' / ' + (info.Creator || '-').trim() + ']' +
                  ' (PDF.js: ' + (PDFJS.version || '-') +
                  (!PDFJS.disableWebGL ? ' [WebGL]' : '') + ')');

      var pdfTitle;
      if (metadata && metadata.has('dc:title')) {
        var title = metadata.get('dc:title');
        // Ghostscript sometimes return 'Untitled', sets the title to 'Untitled'
        if (title !== 'Untitled') {
          pdfTitle = title;
        }
      }

      if (!pdfTitle && info && info['Title']) {
        pdfTitle = info['Title'];
      }

      if (pdfTitle) {
        self.setTitle(pdfTitle + ' - ' + document.title);
      }

      if (info.IsAcroFormPresent) {
        console.warn('Warning: AcroForm/XFA is not supported');
        self.fallback(PDFJS.UNSUPPORTED_FEATURES.forms);
      }

    });
  },

  setInitialView: function pdfViewSetInitialView(storedHash, scale) {
    this.isInitialViewSet = true;

    // When opening a new file (when one is already loaded in the viewer):
    // Reset 'currentPageNumber', since otherwise the page's scale will be wrong
    // if 'currentPageNumber' is larger than the number of pages in the file.
    document.getElementById('pageNumber').value =
      this.pdfViewer.currentPageNumber = 1;

    if (PDFHistory.initialDestination) {
      this.navigateTo(PDFHistory.initialDestination);
      PDFHistory.initialDestination = null;
    } else if (this.initialBookmark) {
      this.setHash(this.initialBookmark);
      PDFHistory.push({ hash: this.initialBookmark }, !!this.initialBookmark);
      this.initialBookmark = null;
    } else if (storedHash) {
      this.setHash(storedHash);
    } else if (scale) {
      this.setScale(scale, true);
      this.page = 1;
    }

    if (this.pdfViewer.currentScale === UNKNOWN_SCALE) {
      // Scale was not initialized: invalid bookmark or scale was not specified.
      // Setting the default one.
      this.setScale(DEFAULT_SCALE, true);
    }
  },

  cleanup: function pdfViewCleanup() {
    this.pdfViewer.cleanup();
    this.pdfThumbnailViewer.cleanup();
    this.pdfDocument.cleanup();
  },

  forceRendering: function pdfViewForceRendering() {
    this.pdfRenderingQueue.printing = this.printing;
    this.pdfRenderingQueue.isThumbnailViewEnabled = this.sidebarOpen;
    this.pdfRenderingQueue.renderHighestPriority();
  },

  setHash: function pdfViewSetHash(hash) {
    if (!this.isInitialViewSet) {
      this.initialBookmark = hash;
      return;
    }

    var validFitZoomValues = ['Fit','FitB','FitH','FitBH',
      'FitV','FitBV','FitR'];

    if (!hash) {
      return;
    }

    if (hash.indexOf('=') >= 0) {
      var params = this.parseQueryString(hash);
      // borrowing syntax from "Parameters for Opening PDF Files"
      if ('nameddest' in params) {
        PDFHistory.updateNextHashParam(params.nameddest);
        this.navigateTo(params.nameddest);
        return;
      }
      var pageNumber, dest;
      if ('page' in params) {
        pageNumber = (params.page | 0) || 1;
      }
      if ('zoom' in params) {
        var zoomArgs = params.zoom.split(','); // scale,left,top
        // building destination array

        // If the zoom value, it has to get divided by 100. If it is a string,
        // it should stay as it is.
        var zoomArg = zoomArgs[0];
        var zoomArgNumber = parseFloat(zoomArg);
        var destName = 'XYZ';
        if (zoomArgNumber) {
          zoomArg = zoomArgNumber / 100;
        } else if (validFitZoomValues.indexOf(zoomArg) >= 0) {
          destName = zoomArg;
        }
        dest = [null, { name: destName },
                zoomArgs.length > 1 ? (zoomArgs[1] | 0) : null,
                zoomArgs.length > 2 ? (zoomArgs[2] | 0) : null,
                zoomArg];
      }
      if (dest) {
        this.pdfViewer.scrollPageIntoView(pageNumber || this.page, dest);
      } else if (pageNumber) {
        this.page = pageNumber; // simple page
      }
      if ('pagemode' in params) {
        if (params.pagemode === 'thumbs' || params.pagemode === 'bookmarks' ||
            params.pagemode === 'attachments') {
          this.switchSidebarView((params.pagemode === 'bookmarks' ?
                                  'outline' : params.pagemode), true);
        } else if (params.pagemode === 'none' && this.sidebarOpen) {
          document.getElementById('sidebarToggle').click();
        }
      }
    } else if (/^\d+$/.test(hash)) { // page number
      this.page = hash;
    } else { // named destination
      PDFHistory.updateNextHashParam(unescape(hash));
      this.navigateTo(unescape(hash));
    }
  },

  switchSidebarView: function pdfViewSwitchSidebarView(view, openSidebar) {
    if (openSidebar && !this.sidebarOpen) {
      document.getElementById('sidebarToggle').click();
    }
    var thumbsView = document.getElementById('thumbnailView');
    var outlineView = document.getElementById('outlineView');
    var attachmentsView = document.getElementById('attachmentsView');

    var thumbsButton = document.getElementById('viewThumbnail');
    var outlineButton = document.getElementById('viewOutline');
    var attachmentsButton = document.getElementById('viewAttachments');

    switch (view) {
      case 'thumbs':
        var wasAnotherViewVisible = thumbsView.classList.contains('hidden');

        thumbsButton.classList.add('toggled');
        outlineButton.classList.remove('toggled');
        attachmentsButton.classList.remove('toggled');
        thumbsView.classList.remove('hidden');
        outlineView.classList.add('hidden');
        attachmentsView.classList.add('hidden');

        this.forceRendering();

        if (wasAnotherViewVisible) {
          this.pdfThumbnailViewer.ensureThumbnailVisible(this.page);
        }
        break;

      case 'outline':
        thumbsButton.classList.remove('toggled');
        outlineButton.classList.add('toggled');
        attachmentsButton.classList.remove('toggled');
        thumbsView.classList.add('hidden');
        outlineView.classList.remove('hidden');
        attachmentsView.classList.add('hidden');

        if (outlineButton.getAttribute('disabled')) {
          return;
        }
        break;

      case 'attachments':
        thumbsButton.classList.remove('toggled');
        outlineButton.classList.remove('toggled');
        attachmentsButton.classList.add('toggled');
        thumbsView.classList.add('hidden');
        outlineView.classList.add('hidden');
        attachmentsView.classList.remove('hidden');

        if (attachmentsButton.getAttribute('disabled')) {
          return;
        }
        break;
    }
  },

  // Helper function to parse query string (e.g. ?param1=value&parm2=...).
  parseQueryString: function pdfViewParseQueryString(query) {
    var parts = query.split('&');
    var params = {};
    for (var i = 0, ii = parts.length; i < ii; ++i) {
      var param = parts[i].split('=');
      var key = param[0].toLowerCase();
      var value = param.length > 1 ? param[1] : null;
      params[decodeURIComponent(key)] = decodeURIComponent(value);
    }
    return params;
  },

  beforePrint: function pdfViewSetupBeforePrint() {
    if (!this.supportsPrinting) {
      var printMessage = mozL10n.get('printing_not_supported', null,
          'Warning: Printing is not fully supported by this browser.');
      this.error(printMessage);
      return;
    }

    var alertNotReady = false;
    var i, ii;
    if (!this.pagesCount) {
      alertNotReady = true;
    } else {
      for (i = 0, ii = this.pagesCount; i < ii; ++i) {
        if (!this.pdfViewer.getPageView(i).pdfPage) {
          alertNotReady = true;
          break;
        }
      }
    }
    if (alertNotReady) {
      var notReadyMessage = mozL10n.get('printing_not_ready', null,
          'Warning: The PDF is not fully loaded for printing.');
      window.alert(notReadyMessage);
      return;
    }

    this.printing = true;
    this.forceRendering();

    var body = document.querySelector('body');
    body.setAttribute('data-mozPrintCallback', true);
    for (i = 0, ii = this.pagesCount; i < ii; ++i) {
      this.pdfViewer.getPageView(i).beforePrint();
    }

  },

  afterPrint: function pdfViewSetupAfterPrint() {
    var div = document.getElementById('printContainer');
    while (div.hasChildNodes()) {
      div.removeChild(div.lastChild);
    }

    this.printing = false;
    this.forceRendering();
  },

  setScale: function (value, resetAutoSettings) {
    this.updateScaleControls = !!resetAutoSettings;
    this.pdfViewer.currentScaleValue = value;
    this.updateScaleControls = true;
  },

  rotatePages: function pdfViewRotatePages(delta) {
    var pageNumber = this.page;

    this.pageRotation = (this.pageRotation + 360 + delta) % 360;
    this.pdfViewer.pagesRotation = this.pageRotation;
    this.pdfThumbnailViewer.pagesRotation = this.pageRotation;

    this.forceRendering();

    this.pdfViewer.scrollPageIntoView(pageNumber);
  },

  /**
   * This function flips the page in presentation mode if the user scrolls up
   * or down with large enough motion and prevents page flipping too often.
   *
   * @this {PDFView}
   * @param {number} mouseScrollDelta The delta value from the mouse event.
   */
  mouseScroll: function pdfViewMouseScroll(mouseScrollDelta) {
    var MOUSE_SCROLL_COOLDOWN_TIME = 50;

    var currentTime = (new Date()).getTime();
    var storedTime = this.mouseScrollTimeStamp;

    // In case one page has already been flipped there is a cooldown time
    // which has to expire before next page can be scrolled on to.
    if (currentTime > storedTime &&
        currentTime - storedTime < MOUSE_SCROLL_COOLDOWN_TIME) {
      return;
    }

    // In case the user decides to scroll to the opposite direction than before
    // clear the accumulated delta.
    if ((this.mouseScrollDelta > 0 && mouseScrollDelta < 0) ||
        (this.mouseScrollDelta < 0 && mouseScrollDelta > 0)) {
      this.clearMouseScrollState();
    }

    this.mouseScrollDelta += mouseScrollDelta;

    var PAGE_FLIP_THRESHOLD = 120;
    if (Math.abs(this.mouseScrollDelta) >= PAGE_FLIP_THRESHOLD) {

      var PageFlipDirection = {
        UP: -1,
        DOWN: 1
      };

      // In presentation mode scroll one page at a time.
      var pageFlipDirection = (this.mouseScrollDelta > 0) ?
                                PageFlipDirection.UP :
                                PageFlipDirection.DOWN;
      this.clearMouseScrollState();
      var currentPage = this.page;

      // In case we are already on the first or the last page there is no need
      // to do anything.
      if ((currentPage === 1 && pageFlipDirection === PageFlipDirection.UP) ||
          (currentPage === this.pagesCount &&
           pageFlipDirection === PageFlipDirection.DOWN)) {
        return;
      }

      this.page += pageFlipDirection;
      this.mouseScrollTimeStamp = currentTime;
    }
  },

  /**
   * This function clears the member attributes used with mouse scrolling in
   * presentation mode.
   *
   * @this {PDFView}
   */
  clearMouseScrollState: function pdfViewClearMouseScrollState() {
    this.mouseScrollTimeStamp = 0;
    this.mouseScrollDelta = 0;
  }
};
window.PDFView = PDFViewerApplication; // obsolete name, using it as an alias


var THUMBNAIL_SCROLL_MARGIN = -19;

/**
 * @constructor
 * @param container
 * @param id
 * @param defaultViewport
 * @param linkService
 * @param renderingQueue
 * @param pageSource
 *
 * @implements {IRenderableView}
 */
var ThumbnailView = function thumbnailView(container, id, defaultViewport,
                                           linkService, renderingQueue,
                                           pageSource) {
  var anchor = document.createElement('a');
  anchor.href = linkService.getAnchorUrl('#page=' + id);
  anchor.title = mozL10n.get('thumb_page_title', {page: id}, 'Page {{page}}');
  anchor.onclick = function stopNavigation() {
    linkService.page = id;
    return false;
  };

  this.pdfPage = undefined;
  this.viewport = defaultViewport;
  this.pdfPageRotate = defaultViewport.rotation;

  this.rotation = 0;
  this.pageWidth = this.viewport.width;
  this.pageHeight = this.viewport.height;
  this.pageRatio = this.pageWidth / this.pageHeight;
  this.id = id;
  this.renderingId = 'thumbnail' + id;

  this.canvasWidth = 98;
  this.canvasHeight = this.canvasWidth / this.pageWidth * this.pageHeight;
  this.scale = (this.canvasWidth / this.pageWidth);

  var div = this.el = document.createElement('div');
  div.id = 'thumbnailContainer' + id;
  div.className = 'thumbnail';

  if (id === 1) {
    // Highlight the thumbnail of the first page when no page number is
    // specified (or exists in cache) when the document is loaded.
    div.classList.add('selected');
  }

  var ring = document.createElement('div');
  ring.className = 'thumbnailSelectionRing';
  ring.style.width = this.canvasWidth + 'px';
  ring.style.height = this.canvasHeight + 'px';

  div.appendChild(ring);
  anchor.appendChild(div);
  container.appendChild(anchor);

  this.hasImage = false;
  this.renderingState = RenderingStates.INITIAL;
  this.renderingQueue = renderingQueue;
  this.pageSource = pageSource;

  this.setPdfPage = function thumbnailViewSetPdfPage(pdfPage) {
    this.pdfPage = pdfPage;
    this.pdfPageRotate = pdfPage.rotate;
    var totalRotation = (this.rotation + this.pdfPageRotate) % 360;
    this.viewport = pdfPage.getViewport(1, totalRotation);
    this.update();
  };

  this.update = function thumbnailViewUpdate(rotation) {
    if (rotation !== undefined) {
      this.rotation = rotation;
    }
    var totalRotation = (this.rotation + this.pdfPageRotate) % 360;
    this.viewport = this.viewport.clone({
      scale: 1,
      rotation: totalRotation
    });
    this.pageWidth = this.viewport.width;
    this.pageHeight = this.viewport.height;
    this.pageRatio = this.pageWidth / this.pageHeight;

    this.canvasHeight = this.canvasWidth / this.pageWidth * this.pageHeight;
    this.scale = (this.canvasWidth / this.pageWidth);

    div.removeAttribute('data-loaded');
    ring.textContent = '';
    ring.style.width = this.canvasWidth + 'px';
    ring.style.height = this.canvasHeight + 'px';

    this.hasImage = false;
    this.renderingState = RenderingStates.INITIAL;
    this.resume = null;
  };

  this.getPageDrawContext = function thumbnailViewGetPageDrawContext() {
    var canvas = document.createElement('canvas');
    canvas.id = 'thumbnail' + id;

    canvas.width = this.canvasWidth;
    canvas.height = this.canvasHeight;
    canvas.className = 'thumbnailImage';
    canvas.setAttribute('aria-label', mozL10n.get('thumb_page_canvas',
      {page: id}, 'Thumbnail of Page {{page}}'));

    div.setAttribute('data-loaded', true);

    ring.appendChild(canvas);

    var ctx = canvas.getContext('2d');
    ctx.save();
    ctx.fillStyle = 'rgb(255, 255, 255)';
    ctx.fillRect(0, 0, this.canvasWidth, this.canvasHeight);
    ctx.restore();
    return ctx;
  };

  this.drawingRequired = function thumbnailViewDrawingRequired() {
    return !this.hasImage;
  };

  this.draw = function thumbnailViewDraw(callback) {
    if (!this.pdfPage) {
      var promise = this.pageSource.getPage(this.id);
      promise.then(function(pdfPage) {
        this.setPdfPage(pdfPage);
        this.draw(callback);
      }.bind(this));
      return;
    }

    if (this.renderingState !== RenderingStates.INITIAL) {
      console.error('Must be in new state before drawing');
    }

    this.renderingState = RenderingStates.RUNNING;
    if (this.hasImage) {
      callback();
      return;
    }

    var self = this;
    var ctx = this.getPageDrawContext();
    var drawViewport = this.viewport.clone({ scale: this.scale });
    var renderContext = {
      canvasContext: ctx,
      viewport: drawViewport,
      continueCallback: function(cont) {
        if (!self.renderingQueue.isHighestPriority(self)) {
          self.renderingState = RenderingStates.PAUSED;
          self.resume = function() {
            self.renderingState = RenderingStates.RUNNING;
            cont();
          };
          return;
        }
        cont();
      }
    };
    this.pdfPage.render(renderContext).promise.then(
      function pdfPageRenderCallback() {
        self.renderingState = RenderingStates.FINISHED;
        callback();
      },
      function pdfPageRenderError(error) {
        self.renderingState = RenderingStates.FINISHED;
        callback();
      }
    );
    this.hasImage = true;
  };

  function getTempCanvas(width, height) {
    var tempCanvas = ThumbnailView.tempImageCache;
    if (!tempCanvas) {
      tempCanvas = document.createElement('canvas');
      ThumbnailView.tempImageCache = tempCanvas;
    }
    tempCanvas.width = width;
    tempCanvas.height = height;
    return tempCanvas;
  }

  this.setImage = function thumbnailViewSetImage(img) {
    if (!this.pdfPage) {
      var promise = this.pageSource.getPage();
      promise.then(function(pdfPage) {
        this.setPdfPage(pdfPage);
        this.setImage(img);
      }.bind(this));
      return;
    }
    if (this.hasImage || !img) {
      return;
    }
    this.renderingState = RenderingStates.FINISHED;
    var ctx = this.getPageDrawContext();

    var reducedImage = img;
    var reducedWidth = img.width;
    var reducedHeight = img.height;

    // drawImage does an awful job of rescaling the image, doing it gradually
    var MAX_SCALE_FACTOR = 2.0;
    if (Math.max(img.width / ctx.canvas.width,
                 img.height / ctx.canvas.height) > MAX_SCALE_FACTOR) {
      reducedWidth >>= 1;
      reducedHeight >>= 1;
      reducedImage = getTempCanvas(reducedWidth, reducedHeight);
      var reducedImageCtx = reducedImage.getContext('2d');
      reducedImageCtx.drawImage(img, 0, 0, img.width, img.height,
                                0, 0, reducedWidth, reducedHeight);
      while (Math.max(reducedWidth / ctx.canvas.width,
                      reducedHeight / ctx.canvas.height) > MAX_SCALE_FACTOR) {
        reducedImageCtx.drawImage(reducedImage,
                                  0, 0, reducedWidth, reducedHeight,
                                  0, 0, reducedWidth >> 1, reducedHeight >> 1);
        reducedWidth >>= 1;
        reducedHeight >>= 1;
      }
    }

    ctx.drawImage(reducedImage, 0, 0, reducedWidth, reducedHeight,
                  0, 0, ctx.canvas.width, ctx.canvas.height);

    this.hasImage = true;
  };
};

ThumbnailView.tempImageCache = null;

/**
 * @typedef {Object} PDFThumbnailViewerOptions
 * @property {HTMLDivElement} container - The container for the thumbs elements.
 * @property {IPDFLinkService} linkService - The navigation/linking service.
 * @property {PDFRenderingQueue} renderingQueue - The rendering queue object.
 */

/**
 * Simple viewer control to display thumbs for pages.
 * @class
 */
var PDFThumbnailViewer = (function pdfThumbnailViewer() {
  /**
   * @constructs
   * @param {PDFThumbnailViewerOptions} options
   */
  function PDFThumbnailViewer(options) {
    this.container = options.container;
    this.renderingQueue = options.renderingQueue;
    this.linkService = options.linkService;

    this.scroll = watchScroll(this.container, this._scrollUpdated.bind(this));
    this._resetView();
  }

  PDFThumbnailViewer.prototype = {
    _scrollUpdated: function PDFThumbnailViewer_scrollUpdated() {
      this.renderingQueue.renderHighestPriority();
    },

    getThumbnail: function PDFThumbnailViewer_getThumbnail(index) {
      return this.thumbnails[index];
    },

    _getVisibleThumbs: function PDFThumbnailViewer_getVisibleThumbs() {
      return getVisibleElements(this.container, this.thumbnails);
    },

    scrollThumbnailIntoView: function (page) {
      var selected = document.querySelector('.thumbnail.selected');
      if (selected) {
        selected.classList.remove('selected');
      }
      var thumbnail = document.getElementById('thumbnailContainer' + page);
      thumbnail.classList.add('selected');
      var visibleThumbs = this._getVisibleThumbs();
      var numVisibleThumbs = visibleThumbs.views.length;

      // If the thumbnail isn't currently visible, scroll it into view.
      if (numVisibleThumbs > 0) {
        var first = visibleThumbs.first.id;
        // Account for only one thumbnail being visible.
        var last = (numVisibleThumbs > 1 ? visibleThumbs.last.id : first);
        if (page <= first || page >= last) {
          scrollIntoView(thumbnail, { top: THUMBNAIL_SCROLL_MARGIN });
        }
      }
    },

    get pagesRotation() {
      return this._pagesRotation;
    },

    set pagesRotation(rotation) {
      this._pagesRotation = rotation;
      for (var i = 0, l = this.thumbnails.length; i < l; i++) {
        var thumb = this.thumbnails[i];
        thumb.update(rotation);
      }
    },

    cleanup: function PDFThumbnailViewer_cleanup() {
      ThumbnailView.tempImageCache = null;
    },

    _resetView: function () {
      this.thumbnails = [];
      this._pagesRotation = 0;
    },

    setDocument: function (pdfDocument) {
      if (this.pdfDocument) {
        // cleanup of the elements and views
        var thumbsView = this.container;
        while (thumbsView.hasChildNodes()) {
          thumbsView.removeChild(thumbsView.lastChild);
        }
        this._resetView();
      }

      this.pdfDocument = pdfDocument;
      if (!pdfDocument) {
        return Promise.resolve();
      }

      return pdfDocument.getPage(1).then(function (firstPage) {
        var pagesCount = pdfDocument.numPages;
        var viewport = firstPage.getViewport(1.0);
        for (var pageNum = 1; pageNum <= pagesCount; ++pageNum) {
          var pageSource = new PDFPageSource(pdfDocument, pageNum);
          var thumbnail = new ThumbnailView(this.container, pageNum,
                                            viewport.clone(), this.linkService,
                                            this.renderingQueue, pageSource);
          this.thumbnails.push(thumbnail);
        }
      }.bind(this));
    },

    ensureThumbnailVisible:
        function PDFThumbnailViewer_ensureThumbnailVisible(page) {
      // Ensure that the thumbnail of the current page is visible
      // when switching from another view.
      scrollIntoView(document.getElementById('thumbnailContainer' + page));
    },

    forceRendering: function () {
      var visibleThumbs = this._getVisibleThumbs();
      var thumbView = this.renderingQueue.getHighestPriority(visibleThumbs,
                                                             this.thumbnails,
                                                             this.scroll.down);
      if (thumbView) {
        this.renderingQueue.renderView(thumbView);
        return true;
      }
      return false;
    }
  };

  return PDFThumbnailViewer;
})();


var DocumentOutlineView = function documentOutlineView(options) {
  var outline = options.outline;
  var outlineView = options.outlineView;
  while (outlineView.firstChild) {
    outlineView.removeChild(outlineView.firstChild);
  }

  if (!outline) {
    return;
  }

  var linkService = options.linkService;

  function bindItemLink(domObj, item) {
    domObj.href = linkService.getDestinationHash(item.dest);
    domObj.onclick = function documentOutlineViewOnclick(e) {
      linkService.navigateTo(item.dest);
      return false;
    };
  }

  var queue = [{parent: outlineView, items: outline}];
  while (queue.length > 0) {
    var levelData = queue.shift();
    var i, n = levelData.items.length;
    for (i = 0; i < n; i++) {
      var item = levelData.items[i];
      var div = document.createElement('div');
      div.className = 'outlineItem';
      var a = document.createElement('a');
      bindItemLink(a, item);
      a.textContent = item.title;
      div.appendChild(a);

      if (item.items.length > 0) {
        var itemsDiv = document.createElement('div');
        itemsDiv.className = 'outlineItems';
        div.appendChild(itemsDiv);
        queue.push({parent: itemsDiv, items: item.items});
      }

      levelData.parent.appendChild(div);
    }
  }
};


var DocumentAttachmentsView = function documentAttachmentsView(options) {
  var attachments = options.attachments;
  var attachmentsView = options.attachmentsView;
  while (attachmentsView.firstChild) {
    attachmentsView.removeChild(attachmentsView.firstChild);
  }

  if (!attachments) {
    return;
  }

  function bindItemLink(domObj, item) {
    domObj.onclick = function documentAttachmentsViewOnclick(e) {
      var downloadManager = new DownloadManager();
      downloadManager.downloadData(item.content, getFileName(item.filename),
                                   '');
      return false;
    };
  }

  var names = Object.keys(attachments).sort(function(a,b) {
    return a.toLowerCase().localeCompare(b.toLowerCase());
  });
  for (var i = 0, ii = names.length; i < ii; i++) {
    var item = attachments[names[i]];
    var div = document.createElement('div');
    div.className = 'attachmentsItem';
    var button = document.createElement('button');
    bindItemLink(button, item);
    button.textContent = getFileName(item.filename);
    div.appendChild(button);
    attachmentsView.appendChild(div);
  }
};



function webViewerLoad(evt) {
  PDFViewerApplication.initialize().then(webViewerInitialized);
}

function webViewerInitialized() {
  var queryString = document.location.search.substring(1);
  var params = PDFViewerApplication.parseQueryString(queryString);
  var file = 'file' in params ? params.file : DEFAULT_URL;

  var fileInput = document.createElement('input');
  fileInput.id = 'fileInput';
  fileInput.className = 'fileInput';
  fileInput.setAttribute('type', 'file');
  fileInput.oncontextmenu = noContextMenuHandler;
  document.body.appendChild(fileInput);

  if (!window.File || !window.FileReader || !window.FileList || !window.Blob) {
    document.getElementById('openFile').setAttribute('hidden', 'true');
    document.getElementById('secondaryOpenFile').setAttribute('hidden', 'true');
  } else {
    document.getElementById('fileInput').value = null;
  }

  var locale = PDFJS.locale || navigator.language;

  if (PDFViewerApplication.preferencePdfBugEnabled) {
    // Special debugging flags in the hash section of the URL.
    var hash = document.location.hash.substring(1);
    var hashParams = PDFViewerApplication.parseQueryString(hash);

    if ('disableworker' in hashParams) {
      PDFJS.disableWorker = (hashParams['disableworker'] === 'true');
    }
    if ('disablerange' in hashParams) {
      PDFJS.disableRange = (hashParams['disablerange'] === 'true');
    }
    if ('disablestream' in hashParams) {
      PDFJS.disableStream = (hashParams['disablestream'] === 'true');
    }
    if ('disableautofetch' in hashParams) {
      PDFJS.disableAutoFetch = (hashParams['disableautofetch'] === 'true');
    }
    if ('disablefontface' in hashParams) {
      PDFJS.disableFontFace = (hashParams['disablefontface'] === 'true');
    }
    if ('disablehistory' in hashParams) {
      PDFJS.disableHistory = (hashParams['disablehistory'] === 'true');
    }
    if ('webgl' in hashParams) {
      PDFJS.disableWebGL = (hashParams['webgl'] !== 'true');
    }
    if ('useonlycsszoom' in hashParams) {
      PDFJS.useOnlyCssZoom = (hashParams['useonlycsszoom'] === 'true');
    }
    if ('verbosity' in hashParams) {
      PDFJS.verbosity = hashParams['verbosity'] | 0;
    }
    if ('ignorecurrentpositiononzoom' in hashParams) {
      IGNORE_CURRENT_POSITION_ON_ZOOM =
        (hashParams['ignorecurrentpositiononzoom'] === 'true');
    }
    if ('locale' in hashParams) {
      locale = hashParams['locale'];
    }
    if ('textlayer' in hashParams) {
      switch (hashParams['textlayer']) {
        case 'off':
          PDFJS.disableTextLayer = true;
          break;
        case 'visible':
        case 'shadow':
        case 'hover':
          var viewer = document.getElementById('viewer');
          viewer.classList.add('textLayer-' + hashParams['textlayer']);
          break;
      }
    }
    if ('pdfbug' in hashParams) {
      PDFJS.pdfBug = true;
      var pdfBug = hashParams['pdfbug'];
      var enabled = pdfBug.split(',');
      PDFBug.enable(enabled);
      PDFBug.init();
    }
  }

  mozL10n.setLanguage(locale);

  if (!PDFViewerApplication.supportsPrinting) {
    document.getElementById('print').classList.add('hidden');
    document.getElementById('secondaryPrint').classList.add('hidden');
  }

  if (!PDFViewerApplication.supportsFullscreen) {
    document.getElementById('presentationMode').classList.add('hidden');
    document.getElementById('secondaryPresentationMode').
      classList.add('hidden');
  }

  if (PDFViewerApplication.supportsIntegratedFind) {
    document.getElementById('viewFind').classList.add('hidden');
  }

  // Listen for unsupported features to trigger the fallback UI.
  PDFJS.UnsupportedManager.listen(
    PDFViewerApplication.fallback.bind(PDFViewerApplication));

  // Suppress context menus for some controls
  document.getElementById('scaleSelect').oncontextmenu = noContextMenuHandler;

  var mainContainer = document.getElementById('mainContainer');
  var outerContainer = document.getElementById('outerContainer');
  mainContainer.addEventListener('transitionend', function(e) {
    if (e.target === mainContainer) {
      var event = document.createEvent('UIEvents');
      event.initUIEvent('resize', false, false, window, 0);
      window.dispatchEvent(event);
      outerContainer.classList.remove('sidebarMoving');
    }
  }, true);

  document.getElementById('sidebarToggle').addEventListener('click',
    function() {
      this.classList.toggle('toggled');
      outerContainer.classList.add('sidebarMoving');
      outerContainer.classList.toggle('sidebarOpen');
      PDFViewerApplication.sidebarOpen =
        outerContainer.classList.contains('sidebarOpen');
      PDFViewerApplication.forceRendering();
    });

  document.getElementById('viewThumbnail').addEventListener('click',
    function() {
      PDFViewerApplication.switchSidebarView('thumbs');
    });

  document.getElementById('viewOutline').addEventListener('click',
    function() {
      PDFViewerApplication.switchSidebarView('outline');
    });

  document.getElementById('viewAttachments').addEventListener('click',
    function() {
      PDFViewerApplication.switchSidebarView('attachments');
    });

  document.getElementById('previous').addEventListener('click',
    function() {
      PDFViewerApplication.page--;
    });

  document.getElementById('next').addEventListener('click',
    function() {
      PDFViewerApplication.page++;
    });

  document.getElementById('zoomIn').addEventListener('click',
    function() {
      PDFViewerApplication.zoomIn();
    });

  document.getElementById('zoomOut').addEventListener('click',
    function() {
      PDFViewerApplication.zoomOut();
    });

  document.getElementById('pageNumber').addEventListener('click', function() {
    this.select();
  });

  document.getElementById('pageNumber').addEventListener('change', function() {
    // Handle the user inputting a floating point number.
    PDFViewerApplication.page = (this.value | 0);

    if (this.value !== (this.value | 0).toString()) {
      this.value = PDFViewerApplication.page;
    }
  });

  document.getElementById('scaleSelect').addEventListener('change',
    function() {
      PDFViewerApplication.setScale(this.value, false);
    });

  document.getElementById('presentationMode').addEventListener('click',
    SecondaryToolbar.presentationModeClick.bind(SecondaryToolbar));

  document.getElementById('openFile').addEventListener('click',
    SecondaryToolbar.openFileClick.bind(SecondaryToolbar));

  document.getElementById('print').addEventListener('click',
    SecondaryToolbar.printClick.bind(SecondaryToolbar));

  document.getElementById('download').addEventListener('click',
    SecondaryToolbar.downloadClick.bind(SecondaryToolbar));


  if (file && file.lastIndexOf('file:', 0) === 0) {
    // file:-scheme. Load the contents in the main thread because QtWebKit
    // cannot load file:-URLs in a Web Worker. file:-URLs are usually loaded
    // very quickly, so there is no need to set up progress event listeners.
    PDFViewerApplication.setTitleUsingUrl(file);
    var xhr = new XMLHttpRequest();
    xhr.onload = function() {
      PDFViewerApplication.open(new Uint8Array(xhr.response), 0);
    };
    try {
      xhr.open('GET', file);
      xhr.responseType = 'arraybuffer';
      xhr.send();
    } catch (e) {
      PDFViewerApplication.error(mozL10n.get('loading_error', null,
        'An error occurred while loading the PDF.'), e);
    }
    return;
  }

  if (file) {
    PDFViewerApplication.open(file, 0);
  }
}

document.addEventListener('DOMContentLoaded', webViewerLoad, true);

document.addEventListener('pagerendered', function (e) {
  var pageIndex = e.detail.pageNumber - 1;
  var pageView = PDFViewerApplication.pdfViewer.getPageView(pageIndex);
  var thumbnailView = PDFViewerApplication.pdfThumbnailViewer.
                      getThumbnail(pageIndex);
  thumbnailView.setImage(pageView.canvas);


  if (pageView.error) {
    PDFViewerApplication.error(mozL10n.get('rendering_error', null,
      'An error occurred while rendering the page.'), pageView.error);
  }


  // If the page is still visible when it has finished rendering,
  // ensure that the page number input loading indicator is hidden.
  if ((pageIndex + 1) === PDFViewerApplication.page) {
    var pageNumberInput = document.getElementById('pageNumber');
    pageNumberInput.classList.remove(PAGE_NUMBER_LOADING_INDICATOR);
  }
}, true);

window.addEventListener('presentationmodechanged', function (e) {
  var active = e.detail.active;
  var switchInProgress = e.detail.switchInProgress;
  PDFViewerApplication.pdfViewer.presentationModeState =
    switchInProgress ? PresentationModeState.CHANGING :
    active ? PresentationModeState.FULLSCREEN : PresentationModeState.NORMAL;
});

function updateViewarea() {
  if (!PDFViewerApplication.initialized) {
    return;
  }
  PDFViewerApplication.pdfViewer.update();
}

window.addEventListener('updateviewarea', function () {
  if (!PDFViewerApplication.initialized) {
    return;
  }

  var location = PDFViewerApplication.pdfViewer.location;

  PDFViewerApplication.store.initializedPromise.then(function() {
    PDFViewerApplication.store.setMultiple({
      'exists': true,
      'page': location.pageNumber,
      'zoom': location.scale,
      'scrollLeft': location.left,
      'scrollTop': location.top
    }).catch(function() {
      // unable to write to storage
    });
  });
  var href = PDFViewerApplication.getAnchorUrl(location.pdfOpenParams);
  document.getElementById('viewBookmark').href = href;
  document.getElementById('secondaryViewBookmark').href = href;

  // Update the current bookmark in the browsing history.
  PDFHistory.updateCurrentBookmark(location.pdfOpenParams, location.pageNumber);

  // Show/hide the loading indicator in the page number input element.
  var pageNumberInput = document.getElementById('pageNumber');
  var currentPage =
    PDFViewerApplication.pdfViewer.getPageView(PDFViewerApplication.page - 1);

  if (currentPage.renderingState === RenderingStates.FINISHED) {
    pageNumberInput.classList.remove(PAGE_NUMBER_LOADING_INDICATOR);
  } else {
    pageNumberInput.classList.add(PAGE_NUMBER_LOADING_INDICATOR);
  }
}, true);

window.addEventListener('resize', function webViewerResize(evt) {
  if (PDFViewerApplication.initialized &&
      (document.getElementById('pageWidthOption').selected ||
       document.getElementById('pageFitOption').selected ||
       document.getElementById('pageAutoOption').selected)) {
    var selectedScale = document.getElementById('scaleSelect').value;
    PDFViewerApplication.setScale(selectedScale, false);
  }
  updateViewarea();

  // Set the 'max-height' CSS property of the secondary toolbar.
  SecondaryToolbar.setMaxHeight(document.getElementById('viewerContainer'));
});

window.addEventListener('hashchange', function webViewerHashchange(evt) {
  if (PDFHistory.isHashChangeUnlocked) {
    PDFViewerApplication.setHash(document.location.hash.substring(1));
  }
});

window.addEventListener('change', function webViewerChange(evt) {
  var files = evt.target.files;
  if (!files || files.length === 0) {
    return;
  }
  var file = files[0];

  if (!PDFJS.disableCreateObjectURL &&
      typeof URL !== 'undefined' && URL.createObjectURL) {
    PDFViewerApplication.open(URL.createObjectURL(file), 0);
  } else {
    // Read the local file into a Uint8Array.
    var fileReader = new FileReader();
    fileReader.onload = function webViewerChangeFileReaderOnload(evt) {
      var buffer = evt.target.result;
      var uint8Array = new Uint8Array(buffer);
      PDFViewerApplication.open(uint8Array, 0);
    };
    fileReader.readAsArrayBuffer(file);
  }

  PDFViewerApplication.setTitleUsingUrl(file.name);

  // URL does not reflect proper document location - hiding some icons.
  document.getElementById('viewBookmark').setAttribute('hidden', 'true');
  document.getElementById('secondaryViewBookmark').
    setAttribute('hidden', 'true');
  document.getElementById('download').setAttribute('hidden', 'true');
  document.getElementById('secondaryDownload').setAttribute('hidden', 'true');
}, true);

function selectScaleOption(value) {
  var options = document.getElementById('scaleSelect').options;
  var predefinedValueFound = false;
  for (var i = 0; i < options.length; i++) {
    var option = options[i];
    if (option.value !== value) {
      option.selected = false;
      continue;
    }
    option.selected = true;
    predefinedValueFound = true;
  }
  return predefinedValueFound;
}

window.addEventListener('localized', function localized(evt) {
  document.getElementsByTagName('html')[0].dir = mozL10n.getDirection();

  PDFViewerApplication.animationStartedPromise.then(function() {
    // Adjust the width of the zoom box to fit the content.
    // Note: If the window is narrow enough that the zoom box is not visible,
    //       we temporarily show it to be able to adjust its width.
    var container = document.getElementById('scaleSelectContainer');
    if (container.clientWidth === 0) {
      container.setAttribute('style', 'display: inherit;');
    }
    if (container.clientWidth > 0) {
      var select = document.getElementById('scaleSelect');
      select.setAttribute('style', 'min-width: inherit;');
      var width = select.clientWidth + SCALE_SELECT_CONTAINER_PADDING;
      select.setAttribute('style', 'min-width: ' +
                                   (width + SCALE_SELECT_PADDING) + 'px;');
      container.setAttribute('style', 'min-width: ' + width + 'px; ' +
                                      'max-width: ' + width + 'px;');
    }

    // Set the 'max-height' CSS property of the secondary toolbar.
    SecondaryToolbar.setMaxHeight(document.getElementById('viewerContainer'));
  });
}, true);

window.addEventListener('scalechange', function scalechange(evt) {
  document.getElementById('zoomOut').disabled = (evt.scale === MIN_SCALE);
  document.getElementById('zoomIn').disabled = (evt.scale === MAX_SCALE);

  var customScaleOption = document.getElementById('customScaleOption');
  customScaleOption.selected = false;

  if (!PDFViewerApplication.updateScaleControls &&
      (document.getElementById('pageWidthOption').selected ||
       document.getElementById('pageFitOption').selected ||
       document.getElementById('pageAutoOption').selected)) {
    updateViewarea();
    return;
  }

  if (evt.presetValue) {
    selectScaleOption(evt.presetValue);
    updateViewarea();
    return;
  }

  var predefinedValueFound = selectScaleOption('' + evt.scale);
  if (!predefinedValueFound) {
    var customScale = Math.round(evt.scale * 10000) / 100;
    customScaleOption.textContent =
      mozL10n.get('page_scale_percent', { scale: customScale }, '{{scale}}%');
    customScaleOption.selected = true;
  }
  updateViewarea();
}, true);

window.addEventListener('pagechange', function pagechange(evt) {
  var page = evt.pageNumber;
  if (evt.previousPageNumber !== page) {
    document.getElementById('pageNumber').value = page;
    PDFViewerApplication.pdfThumbnailViewer.scrollThumbnailIntoView(page);
  }
  var numPages = PDFViewerApplication.pagesCount;

  document.getElementById('previous').disabled = (page <= 1);
  document.getElementById('next').disabled = (page >= numPages);

  document.getElementById('firstPage').disabled = (page <= 1);
  document.getElementById('lastPage').disabled = (page >= numPages);

  // checking if the this.page was called from the updateViewarea function
  if (evt.updateInProgress) {
    return;
  }
  // Avoid scrolling the first page during loading
  if (this.loading && page === 1) {
    return;
  }
  PDFViewerApplication.pdfViewer.scrollPageIntoView(page);
}, true);

function handleMouseWheel(evt) {
  var MOUSE_WHEEL_DELTA_FACTOR = 40;
  var ticks = (evt.type === 'DOMMouseScroll') ? -evt.detail :
              evt.wheelDelta / MOUSE_WHEEL_DELTA_FACTOR;
  var direction = (ticks < 0) ? 'zoomOut' : 'zoomIn';

  if (PresentationMode.active) {
    evt.preventDefault();
    PDFViewerApplication.mouseScroll(ticks * MOUSE_WHEEL_DELTA_FACTOR);
  } else if (evt.ctrlKey) { // Only zoom the pages, not the entire viewer
    evt.preventDefault();
    PDFViewerApplication[direction](Math.abs(ticks));
  }
}

window.addEventListener('DOMMouseScroll', handleMouseWheel);
window.addEventListener('mousewheel', handleMouseWheel);

window.addEventListener('click', function click(evt) {
  if (!PresentationMode.active) {
    if (SecondaryToolbar.opened &&
      PDFViewerApplication.pdfViewer.containsElement(evt.target)) {
      SecondaryToolbar.close();
    }
  } else if (evt.button === 0) {
    // Necessary since preventDefault() in 'mousedown' won't stop
    // the event propagation in all circumstances in presentation mode.
    evt.preventDefault();
  }
}, false);

window.addEventListener('keydown', function keydown(evt) {
  if (OverlayManager.active) {
    return;
  }

  var handled = false;
  var cmd = (evt.ctrlKey ? 1 : 0) |
            (evt.altKey ? 2 : 0) |
            (evt.shiftKey ? 4 : 0) |
            (evt.metaKey ? 8 : 0);

  // First, handle the key bindings that are independent whether an input
  // control is selected or not.
  if (cmd === 1 || cmd === 8 || cmd === 5 || cmd === 12) {
    // either CTRL or META key with optional SHIFT.
    var pdfViewer = PDFViewerApplication.pdfViewer;
    var inPresentationMode = pdfViewer &&
      (pdfViewer.presentationModeState === PresentationModeState.CHANGING ||
       pdfViewer.presentationModeState === PresentationModeState.FULLSCREEN);

    switch (evt.keyCode) {
      case 70: // f
        if (!PDFViewerApplication.supportsIntegratedFind) {
          PDFViewerApplication.findBar.open();
          handled = true;
        }
        break;
      case 71: // g
        if (!PDFViewerApplication.supportsIntegratedFind) {
          PDFViewerApplication.findBar.dispatchEvent('again',
                                                     cmd === 5 || cmd === 12);
          handled = true;
        }
        break;
      case 61: // FF/Mac '='
      case 107: // FF '+' and '='
      case 187: // Chrome '+'
      case 171: // FF with German keyboard
        if (!inPresentationMode) {
          PDFViewerApplication.zoomIn();
        }
        handled = true;
        break;
      case 173: // FF/Mac '-'
      case 109: // FF '-'
      case 189: // Chrome '-'
        if (!inPresentationMode) {
          PDFViewerApplication.zoomOut();
        }
        handled = true;
        break;
      case 48: // '0'
      case 96: // '0' on Numpad of Swedish keyboard
        if (!inPresentationMode) {
          // keeping it unhandled (to restore page zoom to 100%)
          setTimeout(function () {
            // ... and resetting the scale after browser adjusts its scale
            PDFViewerApplication.setScale(DEFAULT_SCALE, true);
          });
          handled = false;
        }
        break;
    }
  }

  // CTRL or META without shift
  if (cmd === 1 || cmd === 8) {
    switch (evt.keyCode) {
      case 83: // s
        PDFViewerApplication.download();
        handled = true;
        break;
    }
  }

  // CTRL+ALT or Option+Command
  if (cmd === 3 || cmd === 10) {
    switch (evt.keyCode) {
      case 80: // p
        SecondaryToolbar.presentationModeClick();
        handled = true;
        break;
      case 71: // g
        // focuses input#pageNumber field
        document.getElementById('pageNumber').select();
        handled = true;
        break;
    }
  }

  if (handled) {
    evt.preventDefault();
    return;
  }

  // Some shortcuts should not get handled if a control/input element
  // is selected.
  var curElement = document.activeElement || document.querySelector(':focus');
  var curElementTagName = curElement && curElement.tagName.toUpperCase();
  if (curElementTagName === 'INPUT' ||
      curElementTagName === 'TEXTAREA' ||
      curElementTagName === 'SELECT') {
    // Make sure that the secondary toolbar is closed when Escape is pressed.
    if (evt.keyCode !== 27) { // 'Esc'
      return;
    }
  }

  if (cmd === 0) { // no control key pressed at all.
    switch (evt.keyCode) {
      case 38: // up arrow
      case 33: // pg up
      case 8: // backspace
        if (!PresentationMode.active &&
          PDFViewerApplication.currentScaleValue !== 'page-fit') {
          break;
        }
        /* in presentation mode */
        /* falls through */
      case 37: // left arrow
        // horizontal scrolling using arrow keys
        if (PDFViewerApplication.pdfViewer.isHorizontalScrollbarEnabled) {
          break;
        }
        /* falls through */
      case 75: // 'k'
      case 80: // 'p'
        PDFViewerApplication.page--;
        handled = true;
        break;
      case 27: // esc key
        if (SecondaryToolbar.opened) {
          SecondaryToolbar.close();
          handled = true;
        }
        if (!PDFViewerApplication.supportsIntegratedFind &&
            PDFViewerApplication.findBar.opened) {
          PDFViewerApplication.findBar.close();
          handled = true;
        }
        break;
      case 40: // down arrow
      case 34: // pg down
      case 32: // spacebar
        if (!PresentationMode.active &&
            PDFViewerApplication.currentScaleValue !== 'page-fit') {
          break;
        }
        /* falls through */
      case 39: // right arrow
        // horizontal scrolling using arrow keys
        if (PDFViewerApplication.pdfViewer.isHorizontalScrollbarEnabled) {
          break;
        }
        /* falls through */
      case 74: // 'j'
      case 78: // 'n'
        PDFViewerApplication.page++;
        handled = true;
        break;

      case 36: // home
        if (PresentationMode.active || PDFViewerApplication.page > 1) {
          PDFViewerApplication.page = 1;
          handled = true;
        }
        break;
      case 35: // end
        if (PresentationMode.active || (PDFViewerApplication.pdfDocument &&
            PDFViewerApplication.page < PDFViewerApplication.pagesCount)) {
          PDFViewerApplication.page = PDFViewerApplication.pagesCount;
          handled = true;
        }
        break;

      case 72: // 'h'
        if (!PresentationMode.active) {
          HandTool.toggle();
        }
        break;
      case 82: // 'r'
        PDFViewerApplication.rotatePages(90);
        break;
    }
  }

  if (cmd === 4) { // shift-key
    switch (evt.keyCode) {
      case 32: // spacebar
        if (!PresentationMode.active &&
            PDFViewerApplication.currentScaleValue !== 'page-fit') {
          break;
        }
        PDFViewerApplication.page--;
        handled = true;
        break;

      case 82: // 'r'
        PDFViewerApplication.rotatePages(-90);
        break;
    }
  }

  if (!handled && !PresentationMode.active) {
    // 33=Page Up  34=Page Down  35=End    36=Home
    // 37=Left     38=Up         39=Right  40=Down
    if (evt.keyCode >= 33 && evt.keyCode <= 40 &&
        !PDFViewerApplication.pdfViewer.containsElement(curElement)) {
      // The page container is not focused, but a page navigation key has been
      // pressed. Change the focus to the viewer container to make sure that
      // navigation by keyboard works as expected.
      PDFViewerApplication.pdfViewer.focus();
    }
    // 32=Spacebar
    if (evt.keyCode === 32 && curElementTagName !== 'BUTTON') {
      if (!PDFViewerApplication.pdfViewer.containsElement(curElement)) {
        PDFViewerApplication.pdfViewer.focus();
      }
    }
  }

  if (cmd === 2) { // alt-key
    switch (evt.keyCode) {
      case 37: // left arrow
        if (PresentationMode.active) {
          PDFHistory.back();
          handled = true;
        }
        break;
      case 39: // right arrow
        if (PresentationMode.active) {
          PDFHistory.forward();
          handled = true;
        }
        break;
    }
  }

  if (handled) {
    evt.preventDefault();
    PDFViewerApplication.clearMouseScrollState();
  }
});

window.addEventListener('beforeprint', function beforePrint(evt) {
  PDFViewerApplication.beforePrint();
});

window.addEventListener('afterprint', function afterPrint(evt) {
  PDFViewerApplication.afterPrint();
});

(function animationStartedClosure() {
  // The offsetParent is not set until the pdf.js iframe or object is visible.
  // Waiting for first animation.
  PDFViewerApplication.animationStartedPromise = new Promise(
      function (resolve) {
    window.requestAnimationFrame(resolve);
  });
})();


